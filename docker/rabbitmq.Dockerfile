FROM rabbitmq as mq

# Define environment variables.
ENV RABBITMQ_USER admin
ENV RABBITMQ_PASSWORD admin
ENV RABBITMQ_PID_FILE /var/lib/rabbitmq/mnesia/rabbitmq

COPY docker/init_rabbitmq.sh /init_rabbitmq.sh
RUN chmod +x /init_rabbitmq.sh

EXPOSE 5672
EXPOSE 15672

RUN rabbitmq-plugins enable --offline rabbitmq_management

# Define default command
CMD ["/init_rabbitmq.sh"]