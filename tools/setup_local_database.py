"""Create private configuration for a fresh local Docker setup; never overwrite it."""
import json
import secrets
from pathlib import Path


def setup(root: Path) -> None:
    local = root / 'artifacts' / 'backend-local'
    targets = [root / '.env', local / 'pgpass', local / 'runtime-env.json']
    if any(path.exists() for path in targets):
        raise FileExistsError('Local configuration already exists; preserved unchanged. See docs/LOCAL_DATABASE.md.')
    local.mkdir(parents=True, exist_ok=True)
    local.chmod(0o700)
    password = secrets.token_urlsafe(32)
    contents = [
        f'POSTGRES_PASSWORD={password}\nPGADMIN_PASSWORD={secrets.token_urlsafe(32)}\n',
        f'postgres:5432:smart_green_local:ad:{password}\n',
        json.dumps({
            'DATABASE_URL': f'postgresql://ad:{password}@127.0.0.1:55432/smart_green_local',
            'SG_DEVICE_ID': 'garden-01',
            'SG_API_KEY': secrets.token_urlsafe(32),
            'SG_WEB_USER': 'admin',
            'SG_WEB_PASSWORD': secrets.token_urlsafe(24),
            'SG_AI_COMMANDS_ENABLED': 'false',
        }, indent=2) + '\n',
    ]
    for path, content in zip(targets, contents):
        with path.open('x') as stream:
            path.chmod(0o600)
            stream.write(content)
    # The container copies this file to its own mode-0600 .pgpass.
    # The enclosing local directory is private on the host.
    targets[1].chmod(0o644)
    print('Created private Docker/backend configuration. No database or device was modified.')


if __name__ == '__main__':
    try:
        setup(Path(__file__).resolve().parents[1])
    except FileExistsError as exc:
        raise SystemExit(str(exc))
