# IBM MQ - KubeMQ Connector

A bidirectional message broker connector that bridges KubeMQ and IBM MQ, enabling seamless message transfer between both systems.

## Overview

This connector provides two-way communication between KubeMQ and IBM MQ message brokers:
- Forward messages from KubeMQ to IBM MQ
- Forward messages from IBM MQ to KubeMQ

## Prerequisites

- Docker installed and running
- Access to KubeMQ broker
- Access to IBM MQ server
- Valid credentials for both systems

## Configuration

The connector uses a YAML configuration file to define the bindings between KubeMQ and IBM MQ. Create a `config.yaml` file with the following structure:

```yaml
bindings:
  - name: kubemq_to_ibm
    type: kubemq_to_ibm_mq
    source:
      address: host.docker.internal:50000        # KubeMQ server address
      queue_name: to_ibm                         # Source queue in KubeMQ
      client_id: kubemq-client                   # Client ID for KubeMQ
      poll_interval_seconds: 1                   # Polling interval
    target:
      host_name: your-ibm-mq-host               # IBM MQ host
      port_number: your-port                     # IBM MQ port
      channel_name: YOUR.CHANNEL                 # IBM MQ channel
      queue_manager: your-queue-manager          # IBM MQ queue manager
      queue_name: YOUR.QUEUE                     # Target queue in IBM MQ
      username: your-username                    # IBM MQ username
      password: your-password                    # IBM MQ password
      poll_interval_ms: 100                      # Polling interval

  - name: ibm_to_kubemq
    type: ibm_mq_to_kubemq
    source:
      host_name: your-ibm-mq-host               # IBM MQ host
      port_number: your-port                     # IBM MQ port
      channel_name: YOUR.CHANNEL                # IBM MQ channel
      queue_manager: your-queue-manager         # IBM MQ queue manager
      queue_name: YOUR.QUEUE                    # Source queue in IBM MQ
      username: your-username                   # IBM MQ username
      password: your-password                   # IBM MQ password
      poll_interval_ms: 100                     # Polling interval
    target:
      address: host.docker.internal:50000       # KubeMQ server address
      queue_name: from_ibm                      # Target queue in KubeMQ
      client_id: kubemq-target                 # Client ID for KubeMQ
```

### Configuration Parameters

#### KubeMQ Configuration
- `address`: KubeMQ server address (format: host:port)
- `queue_name`: Queue name in KubeMQ
- `client_id`: Unique identifier for the KubeMQ client
- `poll_interval_seconds`: Interval for polling messages

#### IBM MQ Configuration
- `host_name`: IBM MQ server hostname or IP address
- `port_number`: IBM MQ listener port
- `channel_name`: IBM MQ channel name
- `queue_manager`: Name of the queue manager
- `queue_name`: Queue name in IBM MQ
- `username`: IBM MQ authentication username
- `password`: IBM MQ authentication password
- `poll_interval_ms`: Interval for polling messages in milliseconds

## Deployment Options

### Docker Deployment

Run the connector using Docker with the following command:

```bash
docker run -it \
  -v ${PWD}/config.yaml:/app/config.yaml \
  europe-docker.pkg.dev/kubemq/images/ibm-mq-connector:v0.1.0
```

This command:
- Mounts your local `config.yaml` file into the container
- Runs the connector in interactive mode
- Uses the specified version of the connector image

### Kubernetes Deployment

The connector can be deployed in a Kubernetes cluster using ConfigMap and Deployment resources.

1. Create a ConfigMap with your configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kubemq-ibmmq-connector-config
data:
  CONFIG: |-
    bindings:
      - name: kubemq_to_ibm
        type: kubemq_to_ibm_mq
        source:
          address: kubemq-cluster-grpc:50000
          queue_name: to_ibm
          client_id: kubemq-client
          poll_interval_seconds: 1
        target:
          host_name: your-ibm-mq-host
          port_number: your-port
          channel_name: YOUR.CHANNEL
          queue_manager: your-queue-manager
          queue_name: YOUR.QUEUE
          username: your-username
          password: your-password
          # message_format: MQHRF2
          # message_ccsid: 1208
          poll_interval_ms: 100
      - name: ibm_to_kubemq
        type: ibm_mq_to_kubemq
        source:
          host_name: your-ibm-mq-host
          port_number: your-port
          channel_name: YOUR.CHANNEL
          queue_manager: your-queue-manager
          queue_name: YOUR.QUEUE
          username: your-username
          password: your-password
          poll_interval_ms: 100
        target:
          address: kubemq-cluster-grpc:50000
          queue_name: from_ibm
          client_id: kubemq-target
```

2. Create a Deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kubemq-ibmmq-connector
  labels:
    app: kubemq-ibmmq-connector
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kubemq-ibmmq-connector
  template:
    metadata:
      labels:
        app: kubemq-ibmmq-connector
    spec:
      containers:
        - name: kubemq-ibmmq-connector
          image: europe-docker.pkg.dev/kubemq/images/ibm-mq-connector:v0.4.0
          volumeMounts:
            - name: config-volume
              mountPath: /app/config.yaml
              subPath: config.yaml
      volumes:
        - name: config-volume
          configMap:
            name: kubemq-ibmmq-connector-config
            items:
              - key: CONFIG
                path: config.yaml
```

3. Apply the configuration:

```bash
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
```

#### Important Kubernetes Notes:
- Ensure the KubeMQ address points to your KubeMQ service in the cluster
- Adjust resource limits and requests based on your needs
- Consider using Kubernetes secrets for sensitive information
- Set appropriate replica count based on your scalability requirements

## Monitoring and Troubleshooting

### Logs
The connector outputs logs to stdout when running in Docker. Monitor these logs for:
- Connection status
- Message transfer confirmations
- Error messages
- Performance metrics

### Common Issues

1. Connection Issues
   - Verify network connectivity to both brokers
   - Check credentials and permissions
   - Ensure correct hostnames and ports

2. Message Transfer Problems
   - Verify queue names exist in both systems
   - Check message format compatibility
   - Ensure sufficient permissions on queues

## Security Considerations

- Store sensitive information (passwords, credentials) securely
- Use encrypted connections when possible
- Regularly rotate credentials
- Follow the principle of least privilege when setting up permissions

## Support

For issues and support:
- Submit issues to the project repository
- Contact the development team
- Check the documentation for updates

## Version History

- v0.1.0: Initial release
  - Basic bidirectional message transfer
  - Configuration via YAML
  - Docker container support