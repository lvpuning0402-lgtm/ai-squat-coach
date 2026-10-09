"""Open the latest saved session HTML: python -m reports.open_latest [--folder]."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import webbrowser


def latest_report(directory='reports'):
    candidates = []
    for path in Path(directory).glob('session_*.json'):
        try:
            report = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(report, dict) or 'session_id' not in report or report.get('report_context') == 'OFFLINE_REPLAY':
                continue
            when = datetime.fromisoformat(report['generated_at']).timestamp()
            candidates.append((when, path.name, path))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    if not candidates:
        raise FileNotFoundError('没有找到训练报告，请先完成一次训练并退出。')
    path = max(candidates)[2].with_suffix('.html')
    if not path.is_file():
        raise FileNotFoundError(f'最新训练没有对应 HTML：{path.name}。可用 reports.replay 生成。')
    return path


def open_path(path):
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(f'文件不存在：{path}')
    if path.is_dir() and os.name == 'nt':
        os.startfile(str(path))
        return True
    try:
        return webbrowser.open(path.as_uri())
    except webbrowser.Error as exc:
        raise OSError(f"无法启动浏览器：{exc}") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path('reports'))
    parser.add_argument('--folder', action='store_true', help='Open the report folder instead.')
    args = parser.parse_args(argv)
    try:
        path = args.directory if args.folder else latest_report(args.directory)
        if not open_path(path):
            raise OSError(f'无法自动打开，请双击：{path.resolve()}')
        print(f'已请求打开：{path.resolve()}')
    except (OSError, ValueError, webbrowser.Error) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    main()
