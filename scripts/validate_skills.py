"""Validate canonical skills, generated standalone copy and distribution integrity."""
from pathlib import Path, PurePosixPath
import hashlib
import re
import sys
from zipfile import ZipFile
from build_distributions import ROOT, SKILLS, MAIN, NAME, modules

errors = []
checks = 0


def check(ok, message):
    global checks
    checks += 1
    if not ok:
        errors.append(message)


def metadata(text, dirname, label):
    m = re.match(r'\A---\nname: ([^\n]+)\ndescription: ([^\n]+)\n---\n', text)
    check(m is not None, f'{label}: required frontmatter')
    if not m:
        return
    name, description = m.groups()
    check(bool(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name)) and len(name) <= 64,
          f'{label}: invalid name')
    check(name == dirname, f'{label}: folder/name mismatch')
    check(0 < len(description) <= 1024, f'{label}: invalid description')
    check('Mehdi Ramdani' in text and '@ramdanimehdi' in text, f'{label}: attribution')


def local_links(text):
    links = re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', text)
    links += [x for x in re.findall(r'`([^`\n]+\.md)`', text) if '/' in x]
    return [x.split('#')[0] for x in links if not re.match(r'[a-z]+:', x) and x.split('#')[0]]


skills = sorted(SKILLS.glob('*/SKILL.md'))
check(len(skills) == 14, 'Expected exactly 14 canonical skills')
for skill in skills:
    metadata(skill.read_text(encoding='utf-8'), skill.parent.name, str(skill.relative_to(ROOT)))
for path in ROOT.rglob('*.md'):
    if '.git' in path.parts:
        continue
    text = path.read_text(encoding='utf-8')
    check(not re.search(r'training\s+bag', text, re.I), f'{path}: incorrect English naming')
    check('sk-' + 'proj-' not in text, f'{path}: unexpected credential marker')
    for link in local_links(text):
        check((path.parent / link).exists(), f'{path.relative_to(ROOT)}: missing {link}')

for required in ['README.md', 'AGENTS.md', 'CLAUDE.md', 'LICENSE', 'NOTICE.md']:
    check((ROOT / required).is_file(), f'Missing {required}')
check('MIT License' in (ROOT / 'LICENSE').read_text(), 'Original documented MIT license not retained')
check((MAIN / 'references/specialist-modules.md').read_text() == modules(), 'Embedded modules stale')
standalone = ROOT / '.claude/skills' / NAME
check(len(list((ROOT / '.claude/skills').glob('*/SKILL.md'))) == 1, 'Expected one unified Claude skill')
for src in MAIN.rglob('*'):
    if src.is_file():
        dst = standalone / src.relative_to(MAIN)
        check(dst.is_file() and dst.read_bytes() == src.read_bytes(), f'Stale Claude copy: {src.name}')
for name in ['LICENSE', 'NOTICE.md']:
    check((standalone / name).read_bytes() == (ROOT / name).read_bytes(), f'Stale {name} in standalone')

with ZipFile(ROOT / 'dist' / f'{NAME}-claude.zip') as z:
    check(z.testzip() is None, 'Claude ZIP CRC failure')
    names = set(z.namelist())
    check(all(PurePosixPath(n).parts[0] == NAME and '..' not in PurePosixPath(n).parts for n in names), 'Unsafe or multi-root ZIP')
    check(f'{NAME}/SKILL.md' in names, 'Missing standalone SKILL.md')
    check(len([n for n in names if n.endswith('/SKILL.md')]) == 1, 'Not a single skill archive')
    for path in standalone.rglob('*'):
        if path.is_file():
            arc = f'{NAME}/{path.relative_to(standalone).as_posix()}'
            check(arc in names and z.read(arc) == path.read_bytes(), f'ZIP differs: {arc}')
            if path.suffix == '.md':
                for link in local_links(path.read_text()):
                    resolved = (path.parent / link).resolve()
                    check(resolved.is_relative_to(standalone.resolve()), f'External standalone dependency: {link}')

with ZipFile(ROOT / 'dist' / f'{NAME}-agent-skills.zip') as z:
    check(z.testzip() is None, 'Full ZIP CRC failure')
    check(len([n for n in z.namelist() if '/.agents/skills/' in n and n.endswith('/SKILL.md')]) == 14, 'Full ZIP missing canonical skills')
    check(not any('/projects/' in n or '/.git/' in n or '/input/' in n for n in z.namelist()), 'Private files in archive')
    for name in z.namelist():
        p = ROOT / PurePosixPath(name).relative_to(NAME)
        check(p.is_file() and z.read(name) == p.read_bytes(), f'Stale source archive: {name}')
for line in (ROOT / 'dist/SHA256SUMS.txt').read_text().splitlines():
    sha, name = line.split('  ', 1)
    check(hashlib.sha256((ROOT / 'dist' / name).read_bytes()).hexdigest() == sha, f'Bad checksum {name}')

print(f'{len(skills)} canonical skills; 1 standalone Claude skill; {checks} structural checks')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print('PASS: metadata, references, attribution, generated copies, archives, checksums')
