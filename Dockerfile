FROM python:alpine
COPY xmllint_action/action.py /
RUN apk add --no-cache libxml2-utils \
 && pip install --no-cache-dir 'github-custom-actions~=2.3'
CMD ["python", "/action.py"]
