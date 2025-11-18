FROM python:alpine
COPY action.py /
RUN apk add --no-cache libxml2-utils \
 && pip install --no-cache-dir git+https://github.com/funkyfuture/github-custom-actions.git@16696f72feba63cc465a130ea0b4c96904ca2f0c
CMD ["python", "/action.py"]
