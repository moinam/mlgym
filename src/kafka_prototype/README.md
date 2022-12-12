Instructions to initialize kafka before running the protoype.

# Kafka Prototype

Instructions to initialize Kafka:

1. Download Java: 
    sudo apt install default-jdk
2. Download Binary file of latest Kafka release: https://kafka.apache.org/downloads
3. Unzip tar file: 
    tar -xzf .\kafka_2.13-3.3.1.tgz then 
    cd .\kafka_2.13-3.3.1
4. Run zookeper server: 
    bin/zookeeper-server-start.sh config/zookeeper.properties
5. Run bootstrap server: 
    bin/kafka-server-start.sh config/server.properties
6. Create a topic to be used by consumer and producer: 
    bin/kafka-topics.sh --create --topic employees --partitions 1 --replication-factor 1 --bootstrap-server localhost:9092

Instructions to run code:

1. Run pip to install all the required packages mentioned in the requirements.txt
   pip install -r .\requirements.txt
2. Run the kafka-produce.py file to first produce messages and send to Kafka Cluster.
   py .\kafka-produce.py
3. Run the kafka-consume.py file to consume the messages produced.
   py .\kafka-consume.py