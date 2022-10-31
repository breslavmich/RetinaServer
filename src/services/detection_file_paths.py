import os


FILES_DIR = "src/client_files"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def create_path(username: str, detection_id: int) -> str:
    path_folders = [FILES_DIR, username, str(detection_id)]
    for i in range(len(path_folders)):
        path = '/'.join(path_folders[:i + 1])
        if not os.path.exists(path):
            os.mkdir(path)
    return '/'.join(path_folders)


def allowed_file(filename: str) -> bool:
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
