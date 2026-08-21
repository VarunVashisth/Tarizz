"""Portable, versioned Tarizz project packages (.tarizz)."""

import hashlib
import json
import os
import tempfile
import zipfile


FORMAT = 'tarizz-project'
VERSION = 1
MAX_FILES = 2000
MAX_UNCOMPRESSED = 2 * 1024 * 1024 * 1024


def _safe_name(name):
    return ''.join(ch if ch.isalnum() or ch in ' ._-' else '_' for ch in name).strip() or 'Project'


def export_project_package(project_id, output_path, db):
    projects = db.get_all_projects()
    project = next((item for item in projects if item['id'] == project_id), None)
    if not project:
        raise ValueError('Project no longer exists.')

    nodes = db.get_all_nodes_for_project(project_id)
    manifest_nodes = []
    media_entries = []
    for node in nodes:
        item = {
            'source_id': node['id'], 'parent_source_id': node.get('parent_id'),
            'node_type': node['node_type'], 'name': node['name'],
            'content': db.load_subpage(node['id']), 'media': [],
        }
        for number, media in enumerate(db.get_media_for_node(node['id'])):
            source = media.get('file_path')
            if not source or not os.path.isfile(source):
                continue
            extension = os.path.splitext(source)[1]
            archive_name = f"media/{node['id']}_{number}{extension}"
            digest = hashlib.sha256()
            with open(source, 'rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            item['media'].append({
                'archive_path': archive_name,
                'media_type': media['media_type'],
                'original_filename': media.get('original_filename') or os.path.basename(source),
                'position_index': media.get('position_index') or '1.0',
                'sha256': digest.hexdigest(),
            })
            media_entries.append((archive_name, source))
        manifest_nodes.append(item)

    manifest = {
        'format': FORMAT, 'version': VERSION,
        'project': {'title': project['title'], 'description': project.get('description') or ''},
        'nodes': manifest_nodes,
    }
    with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        for archive_name, source in media_entries:
            archive.write(source, archive_name)
    return output_path


def _validate_archive(archive):
    infos = archive.infolist()
    if len(infos) > MAX_FILES:
        raise ValueError('Project package contains too many files.')
    if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED:
        raise ValueError('Project package is too large to import safely.')
    names = {info.filename for info in infos}
    if 'manifest.json' not in names:
        raise ValueError('This is not a valid Tarizz project package.')
    for name in names:
        normalized = name.replace('\\', '/')
        if normalized.startswith('/') or '..' in normalized.split('/'):
            raise ValueError('Project package contains an unsafe path.')


def import_project_package(package_path, db):
    copied_media = []
    project_id = None
    with zipfile.ZipFile(package_path, 'r') as archive:
        _validate_archive(archive)
        try:
            manifest = json.loads(archive.read('manifest.json').decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
            raise ValueError('Project manifest is damaged.') from exc
        if manifest.get('format') != FORMAT or manifest.get('version') != VERSION:
            raise ValueError('Unsupported Tarizz project package version.')
        project = manifest.get('project') or {}
        nodes = manifest.get('nodes')
        if not isinstance(nodes, list):
            raise ValueError('Project manifest has no valid node list.')

        project_id = db.create_project(
            _safe_name(str(project.get('title') or 'Imported Project')),
            str(project.get('description') or ''), len(db.get_all_projects()))
        id_map = {}
        pending = list(nodes)
        try:
            while pending:
                progressed = False
                for node in pending[:]:
                    old_parent = node.get('parent_source_id')
                    if old_parent is not None and old_parent not in id_map:
                        continue
                    node_type = node.get('node_type')
                    if node_type not in ('folder', 'subpage', 'flowchart'):
                        raise ValueError('Project contains an unsupported node type.')
                    new_id = db.create_node(project_id, id_map.get(old_parent), node_type,
                                            str(node.get('name') or 'Untitled')[:80])
                    id_map[node.get('source_id')] = new_id
                    content = node.get('content')
                    if content is not None:
                        db.save_subpage(new_id, content)
                    for media in node.get('media') or []:
                        member = media.get('archive_path')
                        if member not in archive.namelist():
                            raise ValueError(f'Missing packaged media: {member}')
                        suffix = os.path.splitext(member)[1]
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                            digest = hashlib.sha256()
                            with archive.open(member) as source:
                                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                                    digest.update(chunk)
                                    temp.write(chunk)
                            temp_path = temp.name
                        try:
                            expected = media.get('sha256')
                            if expected and digest.hexdigest() != expected:
                                raise ValueError(f'Packaged media is damaged: {member}')
                            imported_path = db.import_media_file(temp_path)
                            copied_media.append(imported_path)
                            db.save_media(new_id, media.get('media_type') or 'doc', imported_path,
                                          media.get('original_filename') or os.path.basename(member),
                                          media.get('position_index') or '1.0')
                        finally:
                            try:
                                os.remove(temp_path)
                            except OSError:
                                pass
                    pending.remove(node)
                    progressed = True
                if not progressed:
                    raise ValueError('Project tree contains missing or circular parents.')
        except Exception:
            db.delete_project(project_id)
            for path in copied_media:
                try:
                    os.remove(path)
                except OSError:
                    pass
            raise
    return project_id

