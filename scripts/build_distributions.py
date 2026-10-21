"""Build local Claude skill and reproducible archives; Python 3 stdlib only."""
from pathlib import Path
import hashlib
import shutil
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / '.agents/skills'
NAME = 'training-package-design-specialist'
MAIN = SKILLS / NAME


def modules():
    parts = ['# وحدات التصميم المتخصصة المدمجة\n',
             'Training Package Design Specialist — Mehdi Ramdani — @ramdanimehdi\n',
             'اقرأ هذه الوحدات مع سياسة المصادر ومصفوفة التصميم في هذه الحزمة.\n']
    for skill in sorted(SKILLS.glob('*/SKILL.md')):
        if skill.parent == MAIN:
            continue
        body = skill.read_text(encoding='utf-8').split('---', 2)[2]
        body = body.split('## قاعدة مشتركة إلزامية')[0].strip()
        parts.append(f'\n---\n## {skill.parent.name}\n\n{body}\n')
    return '\n'.join(parts)


def archive(path, entries):
    with ZipFile(path, 'w', compression=ZIP_DEFLATED) as z:
        for name, data in sorted(entries):
            info = ZipInfo(name, date_time=(2026, 10, 21, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)


def build():
    (MAIN / 'references/specialist-modules.md').write_text(modules(), encoding='utf-8')
    target = ROOT / '.claude/skills' / NAME
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(MAIN, target, dirs_exist_ok=True)
    for filename in ('LICENSE', 'NOTICE.md'):
        shutil.copy2(ROOT / filename, target / filename)
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    archive(dist / f'{NAME}-claude.zip', [
        (f'{NAME}/{p.relative_to(target).as_posix()}', p.read_bytes())
        for p in target.rglob('*') if p.is_file()
    ])
    # Full source distribution includes hidden directories but not recursive dist archives.
    entries = [(f'{NAME}/{p.relative_to(ROOT).as_posix()}', p.read_bytes())
               for p in ROOT.rglob('*') if p.is_file()
               and p.relative_to(ROOT).parts[0] not in ('.git', 'dist', 'projects')
               and '__pycache__' not in p.parts and p.suffix != '.pyc']
    archive(dist / f'{NAME}-agent-skills.zip', entries)
    sums = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n'
                   for p in sorted(dist.glob('*.zip')))
    (dist / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8')
    print('Built Claude standalone skill, 2 ZIP archives, and SHA256SUMS.txt')


if __name__ == '__main__':
    build()
