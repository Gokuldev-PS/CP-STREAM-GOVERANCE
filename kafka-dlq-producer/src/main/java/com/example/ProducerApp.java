package com.example;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;
import java.util.Random;

import org.apache.avro.Schema;
import org.apache.avro.generic.GenericData;
import org.apache.avro.generic.GenericRecord;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;

import io.confluent.kafka.serializers.KafkaAvroSerializer;

public class ProducerApp {

    public static void main(String[] args) {

        Properties configProps = new Properties();

        try (FileInputStream fis = new FileInputStream("./values.properties")) {
            configProps.load(fis);
        } catch (IOException e) {
            System.err.println("❌ Failed to load properties file: " + e.getMessage());
            return;
        }

        String bootstrapServers = configProps.getProperty("bootstrap.servers");
        String schemaRegistryUrl = configProps.getProperty("schema.registry.url");
        String topicName = configProps.getProperty("topic.name");

        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put("schema.registry.url", schemaRegistryUrl);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, KafkaAvroSerializer.class.getName());
        props.put("auto.register.schemas", "false");
        props.put("use.latest.version", "true");
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, "true");

        KafkaProducer<String, Object> producer = new KafkaProducer<>(props);
        Random random = new Random();

        int totalRecords = 20;
        for (int i = 0; i < totalRecords; i++) {

            String name = "USERX" + i;
            String email = "USERX" + i + "@example.com";

            // 70% valid SSNs
            String ssn;
            if (random.nextDouble() < 0.7) {
                ssn = String.format("%09d", random.nextInt(1_000_000_000));
            } else {
                ssn = "abc" + random.nextInt(1000);
            }

            GenericRecord record = new GenericData.Record(getSchema());
            record.put("name", name);
            record.put("email", email);
            record.put("ssn", ssn);

            ProducerRecord<String, Object> kafkaRecord = new ProducerRecord<>(topicName, name, record);

            try {
                producer.send(kafkaRecord, (metadata, exception) -> {
                    if (exception != null) {
                        System.out.println("❌ Failed to send record with SSN=" + ssn + ": " + exception.getMessage());
                    } else {
                        System.out.println("✅ Sent record with SSN=" + ssn + " to partition " + metadata.partition());
                    }
                });
            } catch (Exception e) {
                System.out.println("💥 Exception while sending record with SSN=" + ssn + ": " + e.getMessage());
            }
        }

        producer.flush();
        producer.close();
    }

    private static Schema getSchema() {
        String schemaString = """
            {
              "type": "record",
              "name": "plipplip",
              "fields": [
                {"name": "name", "type": "string"},
                {"name": "email", "type": "string"},
                {"name": "ssn", "type": "string"}
              ]
            }
            """;
        return new Schema.Parser().parse(schemaString);
    }
}
