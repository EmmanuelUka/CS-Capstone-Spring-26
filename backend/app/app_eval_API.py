#Test Cases For the Flask API for Player Evaluation

from flask import Flask, jsonify, redirect, request, session

import eval_utility_flask as euf

app = Flask(__name__)

@app.route('/evaluate_recruit', methods=['POST'])
def evaluate_recruit():
    try:
        data = request.get_json()

        if data is None:
            return jsonify({"error": "Invalid or missing JSON"}), 400

        # Validate the incoming data
        is_valid, error_message = euf.validate_player_dict(data)
        if not is_valid:
            return jsonify({"error": error_message}), 400

        # Call function from another module
        result = euf.evaluateRecruit(data)

        return jsonify({
            "message": "Success",
            "result": result
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)