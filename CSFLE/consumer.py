import os
from confluent_kafka import Consumer
from confluent_kafka.serialization import StringDeserializer, SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.json_schema import JSONDeserializer
from confluent_kafka.schema_registry.rules.encryption.encrypt_executor import FieldEncryptionExecutor
from confluent_kafka.schema_registry.rules.encryption.awskms.aws_driver import AwsKmsDriver
from dotenv import load_dotenv
import time

import schema 
from typing import Dict


class User:
    def __init__(self, name: str, favorite_number: int, favorite_color: str):
        self.name = name
        self.favorite_number = favorite_number
        self.favorite_color = favorite_color

    def __str__(self):
        return f"User(name={self.name}, favorite_number={self.favorite_number}, favorite_color={self.favorite_color})"


def dict_to_user(obj: Dict, ctx):
    if obj is None:
        return None
    return User(name=obj.get("name"),
                favorite_number=obj.get("favorite_number"),
                favorite_color=obj.get("favorite_color"))


def get_env(var_name: str) -> str:
    return os.getenv(var_name)


def main():
    load_dotenv()

    # Kafka & Schema Registry configuration
    bootstrap_server = get_env('BOOTSTRAP_SERVER_URL')
    sr_server = get_env('SR_URL')
    kafka_topic = get_env('TOPIC_NAME')

    access_key_id = get_env('AWS_ACCESS_KEY_ID')
    secret_access_key = get_env('AWS_SECRET_ACCESS_KEY')

    # Register encryption support
    AwsKmsDriver.register()
    FieldEncryptionExecutor.register()

    schema_registry_conf = {
        'url': sr_server
    }

    schema_registry_client = SchemaRegistryClient(schema_registry_conf)

    # JSON Deserializer with decryption rule config
    json_deserializer = JSONDeserializer(
        schema_str=schema.USER_SCHEMA,
        schema_registry_client=schema_registry_client,
        from_dict=dict_to_user,
        conf={"use.latest.version": True},
        rule_conf={
            "access.key.id": access_key_id,
            "secret.access.key": secret_access_key
        }
    )

    string_deserializer = StringDeserializer('utf_8')

    consumer_conf = {
        'bootstrap.servers': bootstrap_server,
        'group.id': 'user-consumer-group-1',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': True,
        'security.protocol': 'PLAINTEXT'
    }

    consumer = Consumer(consumer_conf)
    consumer.subscribe([kafka_topic])

    print(f"Consuming messages from topic '{kafka_topic}'...")

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print("Consumer error:", msg.error())
                continue

            user = json_deserializer(msg.value(), SerializationContext(msg.topic(), MessageField.VALUE))
            key = string_deserializer(msg.key(), SerializationContext(msg.topic(), MessageField.KEY))

            if user is not None:
                print(f"Consumed record with key: {key} => {user}")


    except KeyboardInterrupt:
        print("\nExiting...")

    finally:
        consumer.close()


if __name__ == '__main__':
    main()
