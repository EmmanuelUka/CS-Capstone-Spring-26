from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.get('/health')
def health():
    return jsonify({'ok': True})


@app.get('/api/demo-object')
def demo_object():
    return jsonify(
        {
            'id': 'demo-recruit-001',
            'name': 'Jordan Example',
            'position': 'QB',
            'rating': 92,
            'school': 'North Ridge High',
            'offers': ['State University', 'Metro Tech', 'Lake College'],
            'metrics': {
                'height': '6-3',
                'weight': 205,
                'forty': 4.68,
            },
        }
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
