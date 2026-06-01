"""
Processeur Spark AIS — tourne dans Docker (Linux, pas de problème Hadoop/Windows)
Lit depuis ais-raw, filtre/enrichit/déduplique, écrit dans ais-positions.
"""
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_json, struct, when,
    current_timestamp, round as spark_round,
)
from pyspark.sql.types import StructType, StringType, DoubleType, IntegerType

KAFKA  = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
IN     = os.getenv('KAFKA_RAW_TOPIC',         'ais-raw')
OUT    = os.getenv('KAFKA_TOPIC',              'ais-positions')

spark = (
    SparkSession.builder
    .appName('MarineTraffic-AIS')
    .getOrCreate()
)
spark.sparkContext.setLogLevel('WARN')

schema = (
    StructType()
    .add('mmsi',      StringType())
    .add('name',      StringType())
    .add('lat',       DoubleType())
    .add('lng',       DoubleType())
    .add('speed',     DoubleType())
    .add('course',    DoubleType())
    .add('heading',   IntegerType())
    .add('status',    IntegerType())
    .add('ship_type', IntegerType())
    .add('timestamp', StringType())
)

parsed = (
    spark.readStream
    .format('kafka')
    .option('kafka.bootstrap.servers', KAFKA)
    .option('subscribe', IN)
    .option('startingOffsets', 'latest')
    .option('failOnDataLoss', 'false')
    .load()
    .select(from_json(col('value').cast('string'), schema).alias('d'))
    .select('d.*')
)

processed = (
    parsed
    .filter(col('mmsi').isNotNull() & (col('mmsi') != ''))
    .filter(col('lat').between(-90, 90))
    .filter(col('lng').between(-180, 180))
    .filter(col('speed').isNull() | col('speed').between(0, 50))
    .withColumn('type_category',
        when((col('ship_type') >= 70) & (col('ship_type') < 80), 'cargo')
        .when((col('ship_type') >= 80) & (col('ship_type') < 90), 'tanker')
        .when((col('ship_type') >= 60) & (col('ship_type') < 70), 'passenger')
        .when((col('ship_type') >= 30) & (col('ship_type') < 36), 'fishing')
        .otherwise('other')
    )
    .withColumn('lat_r',      spark_round(col('lat'), 3))
    .withColumn('lng_r',      spark_round(col('lng'), 3))
    .withColumn('event_time', current_timestamp())
    .withWatermark('event_time', '30 seconds')
    .dropDuplicates(['mmsi', 'lat_r', 'lng_r'])
    .drop('lat_r', 'lng_r', 'event_time')
)

query = (
    processed
    .select(to_json(struct('*')).alias('value'))
    .writeStream
    .format('kafka')
    .option('kafka.bootstrap.servers', KAFKA)
    .option('topic', OUT)
    .option('checkpointLocation', '/tmp/ais_ck')
    .outputMode('append')
    .start()
)

print(f'✓ Spark : {IN} → filtre/enrichit → {OUT}')
query.awaitTermination()
