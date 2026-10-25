from flask import Blueprint, request, jsonify
from app import db
from app.models.scan import Scan
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.ml.predict import predict_condition, extract_ppg_from_video
from app.ml.recommend import get_recommendation
import tempfile
import os

# Create a blueprint named 'scan' to group all scan related routes
scan = Blueprint('scan', __name__)


def quality_problem(result):
    """If the pulse signal was too poor to trust, return a friendly rescan message."""
    pulse = result.get('pulse') or {}
    if pulse.get('quality') != 'Poor':
        return None
    reason = pulse.get('reason', '')
    if 'Finger' in reason:
        return ("We could not detect your finger. Cover the camera lens and the flash "
                "fully with your fingertip, then scan again.")
    if 'bright' in reason:
        return "The image was too bright. Press a little more lightly and scan again."
    return ("The pulse signal was too unclear to read. Rest your hand on a table, "
            "keep your finger still for the whole scan, and try again.")


def pulse_fields(result):
    """Pulls the new pulse-analysis values out of a prediction result."""
    pulse = result.get('pulse') or {}
    return {
        'regularity': pulse.get('regularity', 'Not recorded'),
        'prv_ms': pulse.get('rmssd_ms'),
        'quality': pulse.get('quality', 'Not recorded'),
    }


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

    problem = quality_problem(result)
    if problem:
        return jsonify({'message': problem}), 400

    pf = pulse_fields(result)
    recommendation = get_recommendation(
        result['condition'], result['heart_rate'], pre_scan_state
    )

    new_scan = Scan(
        user_id=user_id,
        heart_rate=result['heart_rate'] or 0,
        spo2=result['spo2'] or 0,
        condition=result['condition'],
        confidence_score=result['confidence'] or 0,
        recommendation=recommendation,
        pre_scan_state=pre_scan_state,
        pulse_regularity=pf['regularity'],
        prv_ms=pf['prv_ms'] or 0,
        scan_quality=pf['quality']
    )
    db.session.add(new_scan)
    db.session.commit()

    return jsonify({
        'condition': result['condition'],
        'confidence': result['confidence'],
        'heart_rate': result['heart_rate'],
        'spo2': result['spo2'],
        'basis': result.get('basis', ''),
        'regularity': pf['regularity'],
        'prv_ms': pf['prv_ms'],
        'quality': pf['quality'],
        'pre_scan_state': pre_scan_state,
        'scan_id': new_scan.id,
        'recommendation': recommendation
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
        # Extract the colour channel values from every video frame
        raw_signal, fps, error = extract_ppg_from_video(tmp_path)

        if error:
            return jsonify({'message': error}), 400

        # Run the extracted signal through the model and pulse analysis
        result = predict_condition(raw_signal, fps, pre_scan_state)

        if 'error' in result:
            return jsonify({'message': result['error']}), 400

        # Poor-quality scans are rejected and NOT saved
        problem = quality_problem(result)
        if problem:
            return jsonify({'message': problem}), 400

        pf = pulse_fields(result)

        # Plain-language advice (Groq if a key is set, built-in advice otherwise)
        recommendation = get_recommendation(
            result['condition'], result['heart_rate'], pre_scan_state,
            pf['regularity'], result.get('basis', '')
        )

        # Save result to database (0 means "not available")
        new_scan = Scan(
            user_id=user_id,
            heart_rate=result['heart_rate'] or 0,
            spo2=result['spo2'] or 0,
            condition=result['condition'],
            confidence_score=result['confidence'] or 0,
            recommendation=recommendation,
            pre_scan_state=pre_scan_state,
            pulse_regularity=pf['regularity'],
            prv_ms=pf['prv_ms'] or 0,
            scan_quality=pf['quality']
        )
        db.session.add(new_scan)
        db.session.commit()

        return jsonify({
            'condition': result['condition'],
            'confidence': result['confidence'],
            'heart_rate': result['heart_rate'],
            'spo2': result['spo2'],
            'basis': result['basis'],
            'regularity': pf['regularity'],
            'prv_ms': pf['prv_ms'],
            'quality': pf['quality'],
            'pre_scan_state': pre_scan_state,
            'scan_id': new_scan.id,
            'recommendation': recommendation
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
            'pre_scan_state': s.pre_scan_state or 'Not recorded',
            'pulse_regularity': s.pulse_regularity or 'Not recorded',
            'prv_ms': s.prv_ms or 0,
            'scan_quality': s.scan_quality or 'Not recorded',
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
        'pre_scan_state': s.pre_scan_state or 'Not recorded',
        'pulse_regularity': s.pulse_regularity or 'Not recorded',
        'prv_ms': s.prv_ms or 0,
        'scan_quality': s.scan_quality or 'Not recorded',
        'scanned_at': s.scanned_at.strftime('%Y-%m-%d %H:%M:%S')
    }), 200