from flask import Blueprint, request, jsonify
from app import db
from app.models.scan import Scan
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.ml.predict import predict_condition, extract_ppg_from_video
import tempfile
import os

# Create a blueprint named 'scan' to group all scan related routes
scan = Blueprint('scan', __name__)

# ─── PREDICT FROM RAW SIGNAL ────────────────────────────────
@scan.route('/predict', methods=['POST'])
@jwt_required()
def predict():
    user_id = get_jwt_identity()
    data = request.get_json()
    raw_signal = data.get('signal')
    pre_scan_state = data.get('pre_scan_state', 'Resting')

    if not raw_signal:
        return jsonify({'message': 'No signal data provided'}), 400

    result = predict_condition(raw_signal)

    if 'error' in result:
        return jsonify({'message': result['error']}), 400

    new_scan = Scan(
        user_id=user_id,
        heart_rate=result['heart_rate'] or 0,
        spo2=result['spo2'],
        condition=result['condition'],
        confidence_score=result['confidence'],
        recommendation="Groq AI recommendation coming soon."
    )
    db.session.add(new_scan)
    db.session.commit()

    return jsonify({
        'condition': result['condition'],
        'confidence': result['confidence'],
        'heart_rate': result['heart_rate'],
        'spo2': result['spo2'],
        'pre_scan_state': pre_scan_state,
        'scan_id': new_scan.id,
        'recommendation': "Groq AI recommendation coming soon."
    }), 200


# ─── PREDICT FROM VIDEO ─────────────────────────────────────
@scan.route('/predict-video', methods=['POST'])
@jwt_required()
def predict_from_video():
    user_id = get_jwt_identity()

    # Check that a video file was sent
    if 'video' not in request.files:
        return jsonify({'message': 'No video file provided'}), 400

    video_file = request.files['video']
    pre_scan_state = request.form.get('pre_scan_state', 'Resting')

    # Save video to a temporary file for processing
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        video_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # Extract red channel values from every video frame
        raw_signal, fps, error = extract_ppg_from_video(tmp_path)

        if error:
            return jsonify({'message': error}), 400

        # Run the extracted signal through the ML model
        result = predict_condition(raw_signal, fps)

        if 'error' in result:
            return jsonify({'message': result['error']}), 400

        # Save result to database
        new_scan = Scan(
            user_id=user_id,
            heart_rate=result['heart_rate'] or 0,
            spo2=result['spo2'],
            condition=result['condition'],
            confidence_score=result['confidence'],
            recommendation="Groq AI recommendation coming soon."
        )
        db.session.add(new_scan)
        db.session.commit()

        return jsonify({
            'condition': result['condition'],
            'confidence': result['confidence'],
            'heart_rate': result['heart_rate'],
            'spo2': result['spo2'],
            'pre_scan_state': pre_scan_state,
            'scan_id': new_scan.id,
            'recommendation': "Groq AI recommendation coming soon."
        }), 200

    finally:
        # Always delete the temporary video file after processing
        os.unlink(tmp_path)


# ─── GET SCAN HISTORY ───────────────────────────────────────
@scan.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    user_id = get_jwt_identity()
    scans = Scan.query.filter_by(user_id=user_id).order_by(Scan.scanned_at.desc()).all()

    scan_list = []
    for s in scans:
        scan_list.append({
            'id': s.id,
            'heart_rate': s.heart_rate,
            'spo2': s.spo2,
            'condition': s.condition,
            'confidence_score': s.confidence_score,
            'recommendation': s.recommendation,
            'scanned_at': s.scanned_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    return jsonify({'scans': scan_list}), 200


# ─── GET SINGLE SCAN ────────────────────────────────────────
@scan.route('/<int:scan_id>', methods=['GET'])
@jwt_required()
def get_scan(scan_id):
    user_id = get_jwt_identity()
    s = Scan.query.filter_by(id=scan_id, user_id=user_id).first()

    if not s:
        return jsonify({'message': 'Scan not found'}), 404

    return jsonify({
        'id': s.id,
        'heart_rate': s.heart_rate,
        'spo2': s.spo2,
        'condition': s.condition,
        'confidence_score': s.confidence_score,
        'recommendation': s.recommendation,
        'scanned_at': s.scanned_at.strftime('%Y-%m-%d %H:%M:%S')
    }), 200