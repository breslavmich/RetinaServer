import os.path
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.database import User, db, Camera, Detection, Photo
from src.constants.http_status_codes import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_200_OK, \
    HTTP_409_CONFLICT, HTTP_404_NOT_FOUND
from src.services.detection_file_paths import create_path, allowed_file
from werkzeug.utils import secure_filename
from src.services.pattern_recognition_manager import recognize_patterns
from threading import Timer


detect = Blueprint("detect", __name__, url_prefix="/detect")


@detect.post('/camera/add')
@jwt_required()
def add_cam():
    user_id = get_jwt_identity()
    camera = Camera(user_id=user_id)
    db.session.add(camera)
    db.session.commit()

    return jsonify(
        {
            "message": "Camera added successfully!",
            "camera_id": camera.id
        }, HTTP_200_OK
    )


@detect.post('/report')
@jwt_required()
def report_detection():
    user_id = get_jwt_identity()
    user = User.query.filter_by(id=user_id).first()
    camera_id = request.json.get('camera_id')

    if not camera_id:
        return jsonify({
            "Error": "No camera id given"
        }), HTTP_400_BAD_REQUEST

    camera = Camera.query.filter_by(id=camera_id).first()

    if not camera:
        return jsonify({
            "Error": "Invalid camera id"
        }), HTTP_400_BAD_REQUEST

    detection = Detection(user_id=user_id, camera_id=camera_id)
    db.session.add(detection)
    db.session.flush()

    folder_path = create_path(user.username, detection.id)
    detection.folder_path = folder_path
    db.session.commit()

    Timer(180, recognize_patterns)

    return jsonify({
        "message": "Detection reported successfully!",
        "detection_id": detection.id
    }), HTTP_200_OK


@detect.post('/photo')
@jwt_required()
def photo():
    detection_id = request.form.get('detection_id')
    if not detection_id:
        return jsonify({
            "Error": "No detection id given"
        }), HTTP_400_BAD_REQUEST

    detection = Detection.query.filter_by(id=detection_id).first()

    if not detection:
        return jsonify({
            "Error": "Invalid detection id"
        }), HTTP_400_BAD_REQUEST

    if 'file' not in request.files:
        return jsonify({
            "Error": "No file uploaded"
        }), HTTP_400_BAD_REQUEST

    file = request.files['file']

    if not file or file.filename == '':
        return jsonify({
            "Error": "No file uploaded"
        }), HTTP_400_BAD_REQUEST

    if not allowed_file(file.filename):
        return jsonify({
            "Error": "Invalid file extension"
        }), HTTP_400_BAD_REQUEST

    filename = secure_filename(file.filename)
    image_path = os.path.join(detection.folder_path, filename)

    if Photo.query.filter_by(image_path=image_path).first():
        return jsonify({
            "Error": "Image path already exists"
        }), HTTP_409_CONFLICT

    file.save(image_path)

    photo1 = Photo(detection_id=detection_id, image_path=image_path)
    db.session.add(photo1)
    db.session.commit()

    if request.form.get('LAST'):
        recognize_patterns()

    return jsonify({
        "message": "photo uploaded successfully",
        "photo_id": photo1.id
    }), HTTP_200_OK


@detect.get('')
@jwt_required()
def get_all_detections():
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    detections = Detection.query.filter_by(user_id=user_id).paginate(page=page, per_page=per_page)

    data = []

    for detection in detections.items:
        photos = Photo.query.filter_by(detection_id=detection.id)
        paths = {}
        for ph in photos:
            paths[ph.id] = ph.image_path
        data.append({
            "camera_id": detection.camera_id,
            "folder_path": detection.folder_path,
            "images": paths
        })

    meta = {
        'page': detections.page,
        'pages': detections.pages,
        'total_count': detections.total,
        'prev_page': detections.prev_num,
        'next_page': detections.next_num,
        'has_next': detections.has_next,
        'has_prev': detections.has_prev
    }

    return jsonify({"data": data, "meta": meta}), HTTP_200_OK


@detect.get("/get/<int:id>")
@jwt_required()
def get_detection(id):
    current_user = get_jwt_identity()
    detection = Detection.query.filter_by(user_id=current_user, id=id).first()

    if not detection:
        if not Detection.query.filter_by(id=id).first():
            return jsonify({"Error": "No detection with this id"}), HTTP_404_NOT_FOUND
        return jsonify({"Error": "This user can't access this detection"}), HTTP_404_NOT_FOUND

    photos = Photo.query.filter_by(detection_id=detection.id)
    paths = {}
    for ph in photos:
        paths[ph.id] = ph.image_path
    return jsonify({
        "camera_id": detection.camera_id,
        "folder_path": detection.folder_path,
        "images": paths
    }), HTTP_200_OK


