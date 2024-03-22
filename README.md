This is a proof-of-concept hack of putting kepler.gl behind a fastapi,
dynamically rendering data communicated via websockets.

Build:

docker build -t kepler-fastapi-poc .

Run:

docker run -p 8000:8000 kepler-fastapi-poc

View:

http://0.0.0.0:8000/

Post data:

./post_data.sh
