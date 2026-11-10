"""Generate reviewable native startup definitions without registering or running them."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import plistlib
import re
import subprocess
import xml.etree.ElementTree as ET

from .storage import atomic_bytes


TASK_NS = 'http://schemas.microsoft.com/windows/2004/02/mit/task'


def _text(value, label):
    if not isinstance(value, str) or not value or any(ord(char) < 32 for char in value):
        raise ValueError(label + ' must be nonblank text without control characters')
    return value


def _path(value, target, label):
    value = _text(str(value), label)
    path = PureWindowsPath(value) if target == 'windows' else PurePosixPath(value)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError(label + ' must be an absolute ' + target + ' path without parent traversal')
    if target == 'windows':
        # Device/UNC paths create remote or special execution targets, not a local device service.
        if not re.fullmatch(r'[A-Za-z]:', path.drive) or any(char in value for char in '<>"|?*'):
            raise ValueError(label + ' must be an ordinary local Windows drive path')
    elif '\\' in value or re.match(r'^[A-Za-z]:', value):
        raise ValueError(label + ' must use native macOS path syntax')
    return path


def make_plan(platform, config_path, runtime_root, python_path, *, port=4318,
              identity='cherry-meter', user_id=None, uid=None, user_home=None):
    """Return a source-only plan. No file, account, service or process is changed.

    The caller supplies a reviewed native Python executable and stable source root.
    This validates syntax, not target-machine existence or service compatibility.
    """
    if platform not in ('windows', 'macos'):
        raise ValueError('platform must be windows or macos')
    if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,79}', identity):
        raise ValueError('identity must be a short alphanumeric name with dots or hyphens')
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('port must be between 1 and 65535')
    config = _path(config_path, platform, 'config path')
    runtime = _path(runtime_root, platform, 'runtime root')
    python = _path(python_path, platform, 'Python executable')
    launch = runtime / 'native' / 'launch.py'
    argv = [str(python), str(launch), 'collect', '--config', str(config), '--port', str(port)]
    plan = {'contract': 'cherry-meter-lifecycle-plan-v1', 'platform': platform,
            'identity': identity, 'runtime_root': str(runtime), 'config_path': str(config),
            'launch_argv': argv, 'port': port, 'execution_effects': [],
            'registered': False, 'started': False,
            'preconditions': ['Review every path and account before executing any command.',
                'The Python runtime and native/launch.py must already exist on the target machine.',
                'Keep runtime and private configuration at stable paths; regenerate after moving them.',
                'A registration with this identity must not already exist. Do not overwrite another service.',
                'Starting the collector does not configure or qualify any provider export.'],
            'qualifications': ['Plan generation does not install, register, start, stop or remove anything.',
                'Native scheduler behavior, reboot and sleep recovery require testing on the target platform.',
                'Collector downtime and client export loss remain coverage gaps.',
                'Removal commands affect only this startup definition, never configuration or measurement state.']}
    if platform == 'windows':
        user = _text(user_id, 'Windows interactive user ID')
        upper = user.upper()
        principal_name = upper.rsplit('\\', 1)[-1]
        if (principal_name in ('SYSTEM', 'LOCALSYSTEM', 'ADMINISTRATOR', 'ADMINISTRATORS', 'ROOT', 'ADMIN',
                               'LOCAL SERVICE', 'NETWORK SERVICE')
                or upper.startswith(('NT AUTHORITY\\', 'BUILTIN\\'))
                or upper in ('S-1-5-18', 'S-1-5-19', 'S-1-5-20', 'S-1-5-32-544')):
            raise ValueError('a privileged system account is not allowed')
        ET.register_namespace('', TASK_NS)
        def add(parent, name, text=None):
            element = ET.SubElement(parent, '{' + TASK_NS + '}' + name)
            if text is not None:
                element.text = text
            return element
        task = ET.Element('{' + TASK_NS + '}Task', {'version': '1.4'})
        info = add(task, 'RegistrationInfo')
        add(info, 'Description', 'Cherry Meter local metrics collector; user-reviewed startup candidate')
        triggers = add(task, 'Triggers'); logon = add(triggers, 'LogonTrigger')
        add(logon, 'Enabled', 'true'); add(logon, 'UserId', user)
        principals = add(task, 'Principals'); principal = add(principals, 'Principal')
        principal.set('id', 'InteractiveUser')
        add(principal, 'UserId', user); add(principal, 'LogonType', 'InteractiveToken')
        add(principal, 'RunLevel', 'LeastPrivilege')
        settings = add(task, 'Settings')
        for key, value in [('MultipleInstancesPolicy', 'IgnoreNew'), ('DisallowStartIfOnBatteries', 'false'),
                           ('StopIfGoingOnBatteries', 'false'), ('StartWhenAvailable', 'true'),
                           ('RunOnlyIfNetworkAvailable', 'false'), ('AllowStartOnDemand', 'true'),
                           ('Enabled', 'true'), ('Hidden', 'true'), ('WakeToRun', 'false'),
                           ('ExecutionTimeLimit', 'PT0S')]:
            add(settings, key, value)
        restart = add(settings, 'RestartOnFailure')
        add(restart, 'Interval', 'PT1M'); add(restart, 'Count', '3')
        actions = add(task, 'Actions'); actions.set('Context', 'InteractiveUser')
        execute = add(actions, 'Exec')
        add(execute, 'Command', argv[0]); add(execute, 'Arguments', subprocess.list2cmdline(argv[1:]))
        add(execute, 'WorkingDirectory', str(runtime))
        plan.update({'filename': identity + '.task.xml',
                     # No encoding declaration: the same Unicode XML is accepted
                     # as COM XmlText and as an ordinary UTF-8 staged file.
                     'content': ET.tostring(task, encoding='unicode', xml_declaration=False),
                     'user_id': user})
        plan['qualifications'].append('Runs only while the specified user is logged on; no password is saved. A crash is retried at most three times per failure cycle.')
    else:
        if type(uid) is not int or uid < 1:
            raise ValueError('macOS requires the explicit non-root numeric user ID')
        home = _path(user_home, platform, 'macOS user home')
        if str(home) in ('/', '/var/root') or home.name.lower() == 'root':
            raise ValueError('a normal user home is required')
        label = 'local.' + identity
        definition = {'Label': label, 'ProgramArguments': argv, 'WorkingDirectory': str(runtime),
                      'RunAtLoad': True, 'KeepAlive': True, 'ThrottleInterval': 30,
                      'ProcessType': 'Background'}
        plan.update({'filename': label + '.plist', 'content': plistlib.dumps(definition, sort_keys=True).decode('utf-8'),
                     'uid': uid, 'user_home': str(home), 'label': label,
                     'install_destination': str(home / 'Library' / 'LaunchAgents' / (label + '.plist'))})
        plan['qualifications'].append('LaunchAgent starts in the selected user GUI domain, not as root. Stop unloads it for this login; removing its plist prevents future-login startup.')
    plan['sha256'] = hashlib.sha256(plan['content'].encode('utf-8')).hexdigest()
    return plan


def _staging_directory(output_dir):
    path = Path(output_dir).expanduser().absolute()
    # Refuse both lexical and resolved startup paths, including a symlinked parent.
    for candidate in (path, path.resolve()):
        normalized = str(candidate).replace('\\', '/').lower()
        parts = normalized.split('/')
        if ('launchagents' in parts or 'launchdaemons' in parts or 'startup' in parts
                or '/windows/system32/tasks' in normalized or '/windows/tasks' in normalized):
            raise ValueError('output must be a staging directory, never an OS startup/registration directory')
    return path


def write_plan(plan, output_dir):
    """Save a new immutable staged definition and return exact human-only argv.

    Definitions are source artifacts. This function never executes the commands.
    """
    if plan.get('contract') != 'cherry-meter-lifecycle-plan-v1':
        raise ValueError('invalid lifecycle plan')
    filename = plan.get('filename')
    if not isinstance(filename, str) or Path(filename).name != filename or '/' in filename or '\\' in filename:
        raise ValueError('invalid plan filename')
    content = plan.get('content')
    if not isinstance(content, str) or hashlib.sha256(content.encode('utf-8')).hexdigest() != plan.get('sha256'):
        raise ValueError('lifecycle plan content identity mismatch')
    output = _staging_directory(output_dir)
    if output.exists() and not output.is_dir():
        raise ValueError('output must be a staging directory')
    path = output / filename
    atomic_bytes(path, content.encode('utf-8'))
    result = {key: value for key, value in plan.items() if key != 'content'}
    result['plan_file'] = str(path)
    if plan['platform'] == 'windows':
        name = plan['identity']
        result['manual_commands'] = {'install': [['schtasks.exe', '/Create', '/TN', name, '/XML', str(path)]],
            'start': [['schtasks.exe', '/Run', '/TN', name]],
            'status': [['schtasks.exe', '/Query', '/TN', name, '/V', '/FO', 'LIST']],
            'stop': [['schtasks.exe', '/End', '/TN', name]],
            'remove': [['schtasks.exe', '/Delete', '/TN', name]]}
    elif plan['platform'] == 'macos':
        destination = plan['install_destination']; domain = 'gui/' + str(plan['uid'])
        service = domain + '/' + plan['label']
        result['manual_commands'] = {'install': [['/bin/mkdir', '-p', str(PurePosixPath(destination).parent)],
            ['/bin/cp', '-n', str(path), destination], ['/bin/launchctl', 'bootstrap', domain, destination]],
            'start': [['/bin/launchctl', 'kickstart', service]],
            'status': [['/bin/launchctl', 'print', service]],
            'stop': [['/bin/launchctl', 'bootout', service]],
            'remove': [['/bin/launchctl', 'bootout', service], ['/bin/rm', destination]]}
        result['preconditions'] = [*result['preconditions'],
            'Stop if the destination plist already exists. cp -n deliberately will not replace it.',
            'After bootout, bootstrap the reviewed plist again to reload it; kickstart only starts a loaded service.']
        if os.name == 'nt':
            result['qualifications'] = [*result['qualifications'],
                'This plan was staged on Windows. Move it to the target Mac and replace the staged source path in manual copy commands before using them.']
    else:
        raise ValueError('invalid lifecycle platform')
    result['commands_executed'] = False
    return result
