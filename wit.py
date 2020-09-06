# Upload 177
import datetime
import filecmp
import os
import secrets
import shutil
import stat
import sys

import matplotlib.pyplot as plt
import networkx as nx


def init():
    new_path = os.path.join(os.getcwd(), '.wit')
    folders = ['staging_area', 'imeges']
    for folder in folders:
        try:
            os.makedirs(os.path.join(new_path, folder))
        except FileExistsError:
            print(f"The folder {folder} already exists")
    with open(os.path.join(new_path, 'activated.txt'), 'w') as fildata:
        fildata.write("master")


def find_folder(path, to_search):
    if not path:
        raise ValueError(f"No backup folder '{to_search}' found")
    elif not os.path.isabs(path):
        new_path = os.path.join(os.getcwd(), path)
        if os.path.exists(new_path):
            return find_folder(new_path, to_search)
        else:
            raise ValueError(f"I did not find the file at '{path}'")
    elif os.path.isdir(path) and to_search in os.listdir(path):
        return path
    else:
        return find_folder(os.path.dirname(path), to_search)


def handle_remove_error(func, path, exc_info):
    os.chmod(path, stat.S_IRWXU)  # change permission
    os.remove(path)  # remove file


def _delete_an_existing_path(path):
    if os.path.exists(path):
        try:
            os.chmod(path, stat.S_IRWXU)
            os.remove(path)
        except PermissionError:
            shutil.rmtree(path, onerror=handle_remove_error)
    return


def _add_folder(root_folder, relative_path):
    folders = relative_path.split(os.sep)
    i = 0
    folder_path = os.path.join(
        root_folder, '.wit', 'staging_area')
    while i < len(folders) - 1:
        folder_path = os.path.join(folder_path, folders[i])
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)
        i += 1
    return None


def add(file_or_folder_name):
    file_or_folder_name = os.path.normpath(file_or_folder_name)
    wit_folder = find_folder(file_or_folder_name, '.wit')
    relative_path = os.path.relpath(file_or_folder_name, wit_folder)
    backup_path = os.path.join(
        wit_folder, '.wit', 'staging_area', relative_path)
    _delete_an_existing_path(backup_path)
    _add_folder(wit_folder, relative_path)
    if os.path.isfile(file_or_folder_name):
        shutil.copy2(file_or_folder_name, os.path.dirname(backup_path))
    else:
        shutil.copytree(file_or_folder_name, backup_path)


def name_generator():
    characters = '1234567890abcdef'
    password = ''.join(secrets.choice(characters) for i in range(40))
    return password


def creation_and_writing_to_commit_file(parent, commit_path, massage):
    u_tm = datetime.datetime.utcfromtimestamp(0)
    l_tm = datetime.datetime.fromtimestamp(0)
    l_tz = datetime.timezone(l_tm - u_tm)
    dt = datetime.datetime.now()
    t = datetime.datetime(dt.year, dt.month, dt.day, dt.hour,
                          dt.minute, dt.second, int(dt.microsecond), tzinfo=l_tz)
    with open(f'{commit_path}.txt', 'w') as commit_data:
        commit_data.write(
            f"parent={parent}\n"
            + f"date={t.strftime('%c %z')}\n"
            + f"message={massage}"
        )


def backup_copy_folder(src, dst):
    shutil.copytree(src, dst)


def writing_to_references(file_path, commit_id, key):
    if not os.path.exists(file_path):
        with open(f'{file_path}', 'w') as data_file:
            data_file.write(f'HEAD={commit_id}\nmaster={commit_id}\n')
    else:
        with open(f'{file_path}', 'r') as file_data:
            filedata = file_data.read()
        filedata = filedata.replace(
            f'{key}={get_commit(key)}', f'{key}={commit_id}')
        with open(f'{file_path}', 'w') as file_data:
            file_data.write(filedata)


def get_commit(key):
    references_path = os.path.join(wit_path, 'references.txt')
    if os.path.exists(references_path):
        with open(f'{references_path}') as file_data:
            filedata = file_data.readline().strip().split('=')
            while filedata[0] != key or filedata[0] == '':
                filedata = file_data.readline().strip().split('=')
        if filedata:
            return filedata[1]
        raise ValueError(f'Key {key} does not exist')
    return None


def get_branch():
    with open(os.path.join(wit_path, 'activated.txt')) as file_data:
        return file_data.read()


def commit(massage):
    commit_id = name_generator()
    new_commit_folder = os.path.join(images_path, commit_id)
    backup_copy_folder(staging_path, new_commit_folder)
    path_references_file = os.path.join(wit_path, 'references.txt')
    parent = get_commit('HEAD')
    branch = get_branch()
    if branch:
        branch_commit = get_commit(branch)
    else:
        branch_commit = ''
    creation_and_writing_to_commit_file(parent, new_commit_folder, massage)
    writing_to_references(path_references_file, commit_id, 'HEAD')
    if branch_commit == parent:
        writing_to_references(path_references_file, commit_id, branch)


def only_in_one_folder(folder1, folder2):
    """ Returns a list of files that are only in folder2"""
    files_only_folder2 = []

    def recursive_test(dcmp):
        for name in dcmp.right_only:
            files_only_folder2.append(name)
        for sub_dcmp in dcmp.subdirs.values():
            recursive_test(sub_dcmp)
        return files_only_folder2
    dcmp = filecmp.dircmp(folder1, folder2)
    return recursive_test(dcmp)


def diff_files(folder1, folder2):
    """Returns a list of files whose contents are not the same in both folders"""
    changes = []

    def comparison(dcmp):
        for name in dcmp.diff_files:
            changes.append(name)
        for sub_dcmp in dcmp.subdirs.values():
            comparison(sub_dcmp)
        return changes
    dcmp = filecmp.dircmp(folder1, folder2)
    return comparison(dcmp)


def join_the_data(data_list):
    if len(data_list) > 0:
        return '\n\t'.join(data_list)
    return ''


def get_atatus():
    wit_folder = find_folder(os.getcwd(), '.wit')
    commit_id = get_commit('HEAD')
    commit_id_path = os.path.join(images_path, f'{commit_id}')
    changes_not_staged = diff_files(staging_path, wit_folder)
    changes_to_be_committed = set(diff_files(
        staging_path, commit_id_path) + changes_not_staged)
    untracked_files = only_in_one_folder(staging_path, wit_folder)
    return commit_id, changes_to_be_committed, changes_not_staged, untracked_files


def status():
    commit_id, changes_to_be_committed, changes_not_staged, untracked_files = get_atatus()
    print(f'fcommit_id = {commit_id}\n')
    print(
        f'\nChanges to be committed:\n\t{join_the_data(changes_to_be_committed)}')
    print(
        f'\nchanges_not_staged:\n\t{join_the_data(changes_not_staged)}\n')
    print(f'Untracked files:\n\t{join_the_data(untracked_files)}')


def replacing_commit_in_another_folder(commit_path, commit, replace):
    for item in os.listdir(commit_path):
        item_path = os.path.join(commit_path, item)
        if os.path.isfile(item_path):
            file_in_real_path = item_path.replace(
                f'\.wit\images\{commit}', replace)
            _delete_an_existing_path(file_in_real_path)
            shutil.copy2(item_path, file_in_real_path)
        else:
            replacing_commit_in_another_folder(item_path, commit, replace)


def change_brance(branch):
    with open(os.path.join(wit_path, 'activated.txt'), 'w') as filedata:
        filedata.write(branch)


def integrity_check(commit_folder):
    if not os.path.exists(commit_folder):
        raise ValueError(f"{os.path.basename(commit_folder)} does not exist")
    _, changes_to_be_committed, changes_not_staged, _ = get_atatus()
    if len(changes_not_staged) > 0 or len(changes_to_be_committed) > 0:
        raise AssertionError(
            'Some files were not backed up after editing or did not commit')


def checkout(commit_id):  # commit_id can contain a NAME or commit_id
    references_path = os.path.join(wit_path, 'references.txt')
    with open(references_path) as filedata:
        references = filedata.read()
    if commit_id in references:
        change_brance(commit_id)
        commit_id = get_commit(commit_id)
    else:
        change_brance('')
    commit_id_folder = os.path.join(images_path, f'{commit_id}')
    integrity_check(commit_id_folder)
    replacing_commit_in_another_folder(commit_id_folder, commit_id, '')
    writing_to_references(references_path, commit_id, 'HEAD')
    replacing_commit_in_another_folder(
        commit_id_folder, commit_id, '\.wit\staging_area')


def graph():
    G = nx.DiGraph()
    commit_list, connection_list = add_to_graph(get_commit('HEAD'))
    G.add_nodes_from(commit_list)
    G.add_edges_from(connection_list)
    nx.draw(G, with_labels=True, font_weight='bold',
            node_size=2000, font_size=6)
    plt.show()


commit_list = []
connection_list = []


def add_to_graph(commit):
    if len(commit) == 40:
        commit_list.append(commit[:8])
        commit_txt_path = os.path.join(images_path, f'{commit}.txt')
        with open(commit_txt_path, encoding='utf-8') as file_commit:
            parents = file_commit.readline().strip().split('=')[1]
        parents = parents.split(',') if ',' in parents else [parents]
        for parent in parents:
            if parent != 'None':
                connection_list.append((parent[:8], commit[:8]))
                if parent[:8] not in commit_list:
                    add_to_graph(parent)
    return commit_list, connection_list


def branch(NAME):
    references_path = os.path.join(wit_path, 'references.txt')
    commit = get_commit('HEAD')
    with open(references_path, 'a') as filedata:
        filedata.write(f"{NAME}={commit}\n")


def get_a_committed_hierarchy_id(branch):
    start = get_commit(branch)
    if ',' in start:
        next_head = start.split(',')[0]
    nodes = [start]
    next_head = start
    while next_head != 'None':
        head_txt_path = os.path.join(images_path, f'{next_head}.txt')
        with open(head_txt_path, encoding='utf-8') as file_head:
            next_head = file_head.readline().strip().split('=')[1]
            if ',' in next_head:
                next_head = next_head.split(',')[0]
            nodes.append(next_head)
    del nodes[-1]
    return nodes


def common_ground(BRANCH_NAME):
    hierarchy_of_branch_name = get_a_committed_hierarchy_id(
        BRANCH_NAME)
    hierarchy_of_last_commit = get_a_committed_hierarchy_id('HEAD')
    for commit in hierarchy_of_branch_name:
        if commit in hierarchy_of_last_commit:
            return commit
    raise ValueError(
        f"{BRANCH_NAME} cannot merge because it has no common ground with the last commit")


def diff_folders(folder, commit_branch, shared_folder):
    changes = []
    walked = os.walk(folder)
    for base, _, files in walked:
        for file in files:
            file_path = os.path.join(base, file)
            basic_file_path = file_path.replace(commit_branch, shared_folder)
            if not os.path.exists(basic_file_path) or not filecmp.cmp(file_path, basic_file_path):
                changes.append(file_path)
    return changes


def add_a_parent(branch_commit):
    last_commit_path = os.path.join(images_path, get_commit('HEAD'))
    with open(f'{last_commit_path}.txt', 'r') as file_data:
        filedata = file_data.read()
    last_commit = filedata.split('\n')[0].split('=')[1]
    parents = f'{last_commit},{branch_commit}'
    filedata = filedata.replace(f'parent={last_commit}', f'parent={parents}')
    with open(f'{last_commit_path}.txt', 'w') as file_data:
        file_data.write(filedata)


def merge(BRANCH_NAME):
    common_ground_with_branch = common_ground(BRANCH_NAME)
    branch_commit = get_commit(BRANCH_NAME)
    branch_folder = os.path.join(images_path, branch_commit)
    changes = diff_folders(branch_folder, branch_commit,
                           common_ground_with_branch)
    for _file in changes:
        file_in_staging = os.path.join(staging_path, os.path.basename(_file))
        _delete_an_existing_path(file_in_staging)
        shutil.copy2(_file, staging_path)
    commit(f"merge with {BRANCH_NAME}")
    add_a_parent(branch_commit)


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'init':
        init()
    elif len(sys.argv) == 3 and sys.argv[1] == 'add':
        add(sys.argv[2])
    else:
        try:
            wit_folder = find_folder(os.getcwd(), '.wit')
        except ValueError:
            raise ValueError(
                "The '.wit' backup file was not found in the path you entered")
        else:
            wit_path = os.path.join(wit_folder, '.wit')
            staging_path = os.path.join(wit_path, 'staging_area')
            images_path = os.path.join(wit_path, 'images')
            if len(sys.argv) >= 3 and sys.argv[1] == 'commit':
                massage = ' '.join(sys.argv[2:])
                commit(massage)
            elif len(sys.argv) == 2:
                func = {'status': status, 'graph': graph}
                func[sys.argv[1]]()
            elif len(sys.argv) == 3:
                func = {'checkout': checkout, 'branch': branch, 'merge': merge}
                func[sys.argv[1]](sys.argv[2])