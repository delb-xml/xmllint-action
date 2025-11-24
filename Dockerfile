FROM python:alpine
COPY xmllint_action/action.py /
# temporary installation dependency:
RUN apk add --no-cache git
RUN apk add --no-cache libxml2-utils \
 && pip install --no-cache-dir git+https://github.com/funkyfuture/github-custom-actions.git@844aecdc46c969f0c7854b2bcf8de46165cabfcb
CMD ["python", "/action.py"]
