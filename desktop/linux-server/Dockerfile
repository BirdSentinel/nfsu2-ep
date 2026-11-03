# The binary is already compiled and statically linked: no downloads or compiler.
FROM scratch
COPY egyuttparkolas-server /app/egyuttparkolas-server
ENV EP_SERVER_HOME=/data
ENV TOKIO_WORKER_THREADS=1
USER 10001:10001
EXPOSE 8080/tcp
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD ["/app/egyuttparkolas-server", "--healthcheck"]
ENTRYPOINT ["/app/egyuttparkolas-server"]
