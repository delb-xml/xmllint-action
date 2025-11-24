FROM python:alpine
COPY action.py /
# temporary installation dependency:
RUN apk add --no-cache git
RUN apk add --no-cache libxml2-utils \
 && pip install --no-cache-dir git+https://github.com/funkyfuture/github-custom-actions.git@a27a55950a31f6b9c9a6cea4def449c730509686
CMD ["python", "/action.py"]
