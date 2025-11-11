FROM python:alpine
COPY action.py /
RUN apk add --no-cache libxml2-utils \
 && pip install --no-cache-dir github-custom-actions
CMD ["python", "/action.py"]
