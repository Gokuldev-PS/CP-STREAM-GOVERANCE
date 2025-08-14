import os
from uuid import uuid4
from confluent_kafka.schema_registry.rules.encryption.encrypt_executor import FieldEncryptionExecutor
from confluent_kafka.schema_registry.rules.encryption.awskms.aws_driver import AwsKmsDriver
from confluent_kafka import Producer
from confluent_kafka.serialization import StringSerializer, SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient, Rule, RuleKind, RuleMode, RuleParams, Schema, RuleSet
from confluent_kafka.schema_registry.json_schema import JSONSerializer
# from confluent_kafka.schema_registry.avro import AvroSerializer
from dotenv import load_dotenv
from faker import Faker
import random
import time

import schema


class User(object):
    """
    User record

    Args:
        name (str): User's name

        favorite_number (int): User's favorite number

        favorite_color (str): User's favorite color
    """

    def __init__(self, name, favorite_number, favorite_color):
        self.name = name
        self.favorite_number = favorite_number
        self.favorite_color = favorite_color


def user_to_dict(user, ctx):
    """
    Returns a dict representation of a User instance for serialization.

    Args:
        user (User): User instance.

        ctx (SerializationContext): Metadata pertaining to the serialization
            operation.

    Returns:
        dict: Dict populated with user attributes to be serialized.
    """

    return dict(name=user.name,
                favorite_number=user.favorite_number,
                favorite_color=user.favorite_color)


def delivery_report(err, msg):
    """
    Reports the success or failure of a message delivery.

    Args:
        err (KafkaError): The error that occurred on None on success.
        msg (Message): The message that was produced or failed.
    """

    if err is not None:
        print("Delivery failed for User record {}: {}".format(msg.key(), err))
        return
    print('User record {} successfully produced to {} [{}] at offset {}'.format(
        msg.key(), msg.topic(), msg.partition(), msg.offset()))
    

def get_env(var_name: str) -> str:
    return os.getenv(var_name)

def main():
    
    load_dotenv()
    fake = Faker()

    bootstrap_server = get_env('BOOTSTRAP_SERVER_URL')
    kafka_topic=get_env('TOPIC_NAME')

    sr_server=get_env('SR_URL')

    kms_key_id=get_env('KMS_KEY_ID')
    kek_name=get_env('KEK_NAME')

    access_key_id = get_env('AWS_ACCESS_KEY_ID')
    secret_access_key = get_env('AWS_SECRET_ACCESS_KEY')

    # Register the KMS drivers and the field-level encryption executor
    AwsKmsDriver.register()
    FieldEncryptionExecutor.register()
    # print(sr_api_key, sr_api_secret)
    
    schema_registry_conf = {
        'url': sr_server
    }
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)

    rule = Rule(
        "users-encrypt",
        "",
        RuleKind.TRANSFORM,
        RuleMode.WRITEREAD,
        "ENCRYPT",
        ["PII"],
        RuleParams({
            "encrypt.kek.name": kek_name,
            "encrypt.kms.type": get_env('KMS_TYPE'),
            "encrypt.kms.key.id": kms_key_id
        }),
        None,
        None,
        "ERROR,NONE",
        False
    )

    subject = f"{kafka_topic}-value"
    schema_registry_client.register_schema(subject, Schema(
        schema.USER_SCHEMA,
        "JSON",
        [],
        None,
        RuleSet(None, [rule])
    ))

    ser_conf = {'auto.register.schemas': False, 'use.latest.version': True}
    rule_conf = {'secret.access.key': secret_access_key, 'access.key.id': access_key_id}

    json_serializer = JSONSerializer(schema.USER_SCHEMA,
                                     schema_registry_client,
                                     user_to_dict,
                                     conf=ser_conf,
                                     rule_conf=rule_conf)

    string_serializer = StringSerializer('utf_8')

     # Kafka producer configuration
    producer_conf = {
        'bootstrap.servers': bootstrap_server,
        'security.protocol': 'PLAINTEXT'
    }

    producer = Producer(producer_conf)

    print("Producing user records to topic {}. ^C to exit.".format(kafka_topic))
    while True:
        # Serve on_delivery callbacks from previous calls to produce()
        producer.poll(0.0)
        try:
            user_name = fake.name()
            user_favorite_number = random.randint(1, 100)
            user_favorite_color = fake.color_name()

            user = User(name=user_name,
                        favorite_color=user_favorite_color,
                        favorite_number=user_favorite_number)

            producer.produce(topic=kafka_topic,
                             key=string_serializer(str(uuid4())),
                             value=json_serializer(user, SerializationContext(kafka_topic, MessageField.VALUE)),
                             on_delivery=delivery_report)

            time.sleep(1)

        except KeyboardInterrupt:
            break
        except ValueError:
            print("Invalid input, discarding record...")
            continue

    print("\nFlushing records...")
    producer.flush()


if __name__ == '__main__':
    main()