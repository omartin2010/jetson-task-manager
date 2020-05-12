from ..logger import RoboLogger
import signal
import queue
import paho.mqtt.client as mqtt
import traceback
import socket
log = RoboLogger.getLogger()


class MQTTListener(object):
    """
    Description : Class for the MQTT listener for the robot
    """
    # Defines constants for this class
    __LOG_MQTTLISTENER_GRACEFUL_SHUTDOWN = 'mqtt_listener_graceful_shutdown'
    __LOG_MQTTLISTENER_RUN = 'mqtt_listener_run'
    __LOG_MQTTLISTENER_THREAD_MAIN = 'mqtt_listener_thread_main'
    __LOG_MQTTLISTENER_ON_CONNECT = 'mqtt_listener_on_connect'
    __LOG_MQTTLISTENER_ON_MESSAGE = 'mqtt_listener_on_message'
    __LOG_MQTTLISTENER_ON_DISCONNECT = 'mqtt_listener_on_distonnect'
    __LOG_MQTTLISTENER_ON_SUBSCRIBE = 'mqtt_listener_on_subscribe'
    __REQUIRED_KEYS = ['brokerIP',
                       'brokerPort',
                       'brokerProto',
                       'clientID',
                       'subscribedTopics',
                       'publishingTopics']

    def __init__(
            self,
            mqtt_configuration) -> None:
        """
        Description :
            class initializer.
        Args:
            mqtt_configuration : dict, configuration dict that tells where to
                connect, which topics to listen to, etc.
        """
        try:
            if not isinstance(mqtt_configuration, dict):
                raise TypeError('mqtt_configuration has to be a dictionnary')
            diff = list(
                set(self.__REQUIRED_KEYS) - set(mqtt_configuration.keys()))
            if len(diff) != 0:
                raise KeyError(f'Missing some keys in the config dictionnary '
                               f' = {diff}.')
            try:
                socket.inet_aton(str(mqtt_configuration['brokerIP']))
            except:
                raise OSError(f'Poorly formatted IP address')
            if mqtt_configuration['brokerProto'] != 'tcp':
                raise ValueError('broker proto has to be tcp')
            if not isinstance(mqtt_configuration['clientID'], str):
                raise ValueError('clientID has to be a string')
            if not isinstance(mqtt_configuration['subscribedTopics'], list):
                raise ValueError(f'subscribedTopics has to be a list '
                                 f'of strings')
            for topic in mqtt_configuration['subscribedTopics']:
                if not isinstance(topic, str):
                    raise TypeError(f'subscribed topic has to be '
                                    f'a string : {str(topic)}')
            if not isinstance(mqtt_configuration['publishingTopics'], list):
                raise ValueError(f'publishingTopics has to be a list '
                                 f'of strings')
            for topic in mqtt_configuration['publishingTopics']:
                if not isinstance(topic, str):
                    raise TypeError(f'publishing topic has to be '
                                    f'a string : {str(topic)}')
            self.mqtt_configuration = mqtt_configuration
            self.mqtt_message_queue = queue.Queue()
            self.running = False
        except Exception:
            raise

    def graceful_shutdown(
            self,
            s=None) -> None:
        """
        Description :
            Graceful shutdown for the MQTT listener
        Args:
            None
        """
        try:
            if s is not None:
                if s not in signal.Signals:
                    raise TypeError('input parameter \'s\' has to be a signal')
                log.critical(self.__LOG_MQTTLISTENER_GRACEFUL_SHUTDOWN,
                             msg=f'Initiating graceful shutdown now '
                                 f'from received signal {s.name}.')
            else:
                log.critical(self.__LOG_MQTTLISTENER_GRACEFUL_SHUTDOWN,
                             msg=f'Initiating graceful shutdown now '
                                 f'from non signal.')
            # Stop MQTT client:
            try:
                self.mqttClient.loop_stop()
                self.mqttClient.disconnect()
                if self.mqttClient.is_connected():
                    log.error(self.__LOG_MQTTLISTENER_GRACEFUL_SHUTDOWN,
                              msg=f'Unable to stop MQTT client.')
                else:
                    log.info(self.__LOG_MQTTLISTENER_GRACEFUL_SHUTDOWN,
                             msg=f'Stopped MQTT client.')
            except:
                log.error(self.__LOG_MQTTLISTENER_GRACEFUL_SHUTDOWN,
                          msg=f'Exception in shutting down MQTT')
                raise
        except:
            raise

    def run(self) -> None:
        """
        Description : starts the listener
        """
        # Launch the MQTT thread listener
        log.warning(self.__LOG_MQTTLISTENER_RUN,
                    msg='Launching MQTT Connection.')
        try:
            mqtt_default_qos = 2
            self.mqtt_topics = [(topic, mqtt_default_qos)
                                for topic in self.mqtt_configuration
                                ['subscribedTopics']]
            self.mqttClient = mqtt.Client(
                client_id=self.mqtt_configuration["clientID"],
                clean_session=True,
                transport=self.mqtt_configuration["brokerProto"])
            self.mqttClient.enable_logger(
                logger=RoboLogger.getSpecificLogger(
                    self.__LOG_MQTTLISTENER_THREAD_MAIN))
            self.mqttClient.on_subscribe = self.on_subscribe
            self.mqttClient.on_connect = self.on_connect
            self.mqttClient.on_disconnect = self.on_disconnect
            self.mqttClient.on_message = self.on_message
            self.mqttClient.connect(
                host=self.mqtt_configuration["brokerIP"],
                port=self.mqtt_configuration["brokerPort"])
            log.warning(self.__LOG_MQTTLISTENER_RUN,
                        msg='Launching MQTT Thread (loop start).')
            self.mqttClient.loop_start()
            self.running = True

        except Exception:
            log.error(self.__LOG_MQTTLISTENER_THREAD_MAIN,
                      f'Error : {traceback.print_exc()}')
        finally:
            log.warning(self.__LOG_MQTTLISTENER_THREAD_MAIN,
                        msg=f'Exiting MQTT connection thread.')

    def on_connect(self, client, userdata, flags, rc):
        log.info(self.__LOG_MQTTLISTENER_ON_CONNECT,
                 msg=f'Connected to MQTT broker. Result code {str(rc)}')
        mqtt_connect_result, self.mqtt_connect_mid = \
            client.subscribe(self.mqtt_topics)
        if mqtt_connect_result == mqtt.MQTT_ERR_SUCCESS:
            log.warning(self.__LOG_MQTTLISTENER_ON_CONNECT,
                        msg=f'Successfully subscribed to '
                            f'topics in input config file')
            log.debug(self.__LOG_MQTTLISTENER_ON_CONNECT,
                      msg=f'Topics subcribed = {self.mqtt_topics}')
            self.subscribed_mqtt_topics = \
                [topic for topic, qos in self.mqtt_topics]
        else:
            log.error(self.__LOG_MQTTLISTENER_ON_CONNECT,
                      msg=f'MQTT Broker subscription problem.')
            self.subscribed_mqtt_topics = []

    def on_message(self, client, userdata, message):
        """ callback function used for the mqtt client (called when
        a new message is publisehd to one of the queues we subscribe to)
        """
        log.info(self.__LOG_MQTTLISTENER_ON_MESSAGE,
                 msg=f'Received MID {message.mid} : '
                     f'"{str(message.payload)}" '
                     f'on topic {message.topic} with QoS {message.qos}')
        self.mqtt_message_queue.put_nowait(message)

    def on_disconnect(self, client, userdata, rc=0):
        """callback for handling disconnects
        """
        log.warning(self.__LOG_MQTTLISTENER_ON_DISCONNECT,
                    f'Disconnected MQTT result code = {rc}. '
                    f'Should automatically re-connect to broker')
        self.mqttClient.loop_stop()

    def on_subscribe(self, client, userdata, mid, granted_qos):
        if mid == self.mqtt_connect_mid:
            log.debug(self.__LOG_MQTTLISTENER_ON_SUBSCRIBE,
                      msg=f'Subscribed to topics. Granted '
                          f'QOS = {granted_qos}')
        else:
            log.error(self.__LOG_MQTTLISTENER_ON_SUBSCRIBE,
                      msg=f'Strange... MID does not match '
                          f'self.mqtt_connect_mid')
