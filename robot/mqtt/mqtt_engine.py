from ..logger import RoboLogger
from ..message import Message
import signal
import asyncio
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
import traceback
import socket
log = RoboLogger.getLogger()


class Singleton(object):
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
        return class_._instance


class MQTTEngine(object, Singleton):
    """
    Description : Class for the MQTT Engine for the robot
    """
    # Defines constants for this class
    __LOG_GRACEFUL_SHUTDOWN = 'mqtt_engine_graceful_shutdown'
    __LOG_RUN = 'mqtt_engine_run'
    __LOG_THREAD_MAIN = 'mqtt_engine_thread_main'
    __LOG_ON_CONNECT = 'mqtt_engine_on_connect'
    __LOG_ON_MESSAGE = 'mqtt_engine_on_message'
    __LOG_ON_DISCONNECT = 'mqtt_engine_on_distonnect'
    __LOG_ON_SUBSCRIBE = 'mqtt_engine_on_subscribe'
    __LOG_OUTBOUND_MSG_SENDER = 'mqtt_engine_outbound_msg_sender'
    __REQUIRED_KEYS = ['brokerIP',
                       'brokerPort',
                       'brokerProto',
                       'clientID',
                       'subscribedTopics',
                       'publishingTopics']

    def __init__(
            self,
            mqtt_configuration: dict,
            event_loop: asyncio.BaseEventLoop) -> None:
        """
        Description :
            class initializer.
        Args:
            mqtt_configuration : dict, configuration dict that tells where to
                connect, which topics to listen to, etc.
            event_loop : base
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
            if not isinstance(event_loop, asyncio.BaseEventLoop):
                raise TypeError(f'Constructor requires event_loop to be of '
                                f'asyncio.BaseEventLoop() class')
            self.mqtt_configuration = mqtt_configuration
            self.in_msg_q = asyncio.Queue()
            self.out_msg_q = asyncio.Queue()
            self.__event_loop = event_loop
            self.running_async_tasks = []
            self._running = False
            self.__mqtt_client_id = self.mqtt_configuration["clientID"],
            self.__mqtt_transport = self.mqtt_configuration["brokerProto"]
            self.__mqtt_broker_ip = self.mqtt_configuration["brokerIP"]
            self.__mqtt_port = self.mqtt_configuration["brokerPort"]
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
                log.critical(self.__LOG_GRACEFUL_SHUTDOWN,
                             msg=f'Initiating graceful shutdown now '
                                 f'from received signal {s.name}.')
            else:
                log.critical(self.__LOG_GRACEFUL_SHUTDOWN,
                             msg=f'Initiating graceful shutdown now '
                                 f'from non signal.')
            # Stop MQTT client:
            try:
                self._mqtt_client.loop_stop()
                self._mqtt_client.disconnect()
                if self._mqtt_client.is_connected():
                    log.error(self.__LOG_GRACEFUL_SHUTDOWN,
                              msg=f'Unable to stop MQTT client.')
                else:
                    log.info(self.__LOG_GRACEFUL_SHUTDOWN,
                             msg=f'Stopped MQTT client.')
            except:
                log.error(self.__LOG_GRACEFUL_SHUTDOWN,
                          msg=f'Exception in shutting down MQTT')
                raise
        except:
            raise

    def run(self) -> None:
        """
        Description : starts the listener
        """
        # Launch the MQTT thread listener
        log.warning(self.__LOG_RUN,
                    msg='Launching MQTT Connection.')
        try:
            mqtt_default_qos = 2
            self.mqtt_topics = [(topic, mqtt_default_qos)
                                for topic in self.mqtt_configuration
                                ['subscribedTopics']]
            self._mqtt_client = mqtt.Client(
                client_id=self.__mqtt_client_id,
                clean_session=True,
                transport=self.__mqtt_transport)
            self._mqtt_client.enable_logger(
                logger=RoboLogger.getSpecificLogger(
                    self.__LOG_THREAD_MAIN))
            self._mqtt_client.on_subscribe = self.__cb_mqtt_on_subscribe
            self._mqtt_client.on_connect = self.__cb_mqtt_on_connect
            self._mqtt_client.on_disconnect = self.__cb_mqtt_on_disconnect
            self._mqtt_client.on_message = self.__cb_mqtt_on_message
            self._mqtt_client.connect(
                host=self.__mqtt_broker_ip,
                port=self.__mqtt_port)
            log.warning(self.__LOG_RUN,
                        msg='Launching MQTT Thread (loop start).')
            self._mqtt_client.loop_start()
            self._running = True
            # create task on the event loop for processing outbound messages
            self.running_async_tasks.append(
                self.__event_loop.create_task(self._outbound_message_sender()))

        except Exception:
            log.error(self.__LOG_THREAD_MAIN,
                      f'Error : {traceback.print_exc()}')
        finally:
            log.warning(self.__LOG_THREAD_MAIN,
                        msg=f'Exiting MQTT connection thread.')

    def subscribe_topic(self,
                        callback,
                        topic: str,
                        qos: int = 0) -> None:
        """
        Description :
            Quickly subscribes to a topic and registers a callback for
                responses.
        """
        # Type and value checking
        if not callable(callback):
            raise TypeError(f'callback should be a callable function.')
        if not isinstance(topic, str):
            raise TypeError(f'Topic has to be a string')
        if qos not in [0, 1, 2]:
            raise ValueError(f'qos has to be 0, 1 or 2')
        try:
            subscribe.callback(
                callback=callback,
                topics=[topic],
                qos=qos,
                hostname=self.__mqtt_broker_ip,
                port=self.__mqtt_port,
                client_id=self.__mqtt_client_id,
                transport=self.__mqtt_transport)
        except:
            raise Exception(f'Exception {traceback.print_exc()}')
        return None

    def __cb_mqtt_on_connect(self, client, userdata, flags, rc):
        log.info(self.__LOG_ON_CONNECT,
                 msg=f'Connected to MQTT broker. Result code {str(rc)}')
        mqtt_connect_result, self.mqtt_connect_mid = \
            client.subscribe(self.mqtt_topics)
        if mqtt_connect_result == mqtt.MQTT_ERR_SUCCESS:
            log.warning(self.__LOG_ON_CONNECT,
                        msg=f'Successfully subscribed to '
                            f'topics in input config file')
            log.debug(self.__LOG_ON_CONNECT,
                      msg=f'Topics subcribed = {self.mqtt_topics}')
            self.subscribed_mqtt_topics = \
                [topic for topic, qos in self.mqtt_topics]
        else:
            log.error(self.__LOG_ON_CONNECT,
                      msg=f'MQTT Broker subscription problem.')
            self.subscribed_mqtt_topics = []

    def __cb_mqtt_on_message(self, client, userdata, message):
        """ callback function used for the mqtt client (called when
        a new message is publisehd to one of the queues we subscribe to)
        """
        log.info(self.__LOG_ON_MESSAGE,
                 msg=f'Received MID {message.mid} : '
                     f'"{str(message.payload)}" '
                     f'on topic {message.topic} with QoS {message.qos}')
        try:
            self.in_msg_q.put_nowait(
                (message.topic,
                 message.payload.decode('utf-8')))
        except asyncio.QueueFull:
            raise asyncio.QueueFull('Unable to write to mqtt_message_queue')

    def __cb_mqtt_on_disconnect(self, client, userdata, rc=0):
        """callback for handling disconnects
        """
        log.warning(self.__LOG_ON_DISCONNECT,
                    f'Disconnected MQTT result code = {rc}. '
                    f'Should automatically re-connect to broker')
        self._mqtt_client.loop_stop()

    def __cb_mqtt_on_subscribe(self, client, userdata, mid, granted_qos):
        if mid == self.mqtt_connect_mid:
            log.debug(self.__LOG_ON_SUBSCRIBE,
                      msg=f'Subscribed to topic(s). Granted '
                          f'QOS = {granted_qos}')
        else:
            log.error(self.__LOG_ON_SUBSCRIBE,
                      msg=f'Strange... MID does not match '
                          f'self.mqtt_connect_mid')

    async def _outbound_message_sender(self):
        """
        Description : loop that takes care of sending new messages as they
            are added to the out_msg_q queue.
        """
        while True:
            try:
                msg = Message(await self.out_msg_q.get())
                # Construct payload for mqtt message
                payload = {
                    'src_node_id': msg.src_node_id,
                    'dst_node_id': msg.dst_node_id,
                    'msg_node_id': msg.msg_id
                }
                payload.update(msg.body)
                self._mqtt_client.publish(
                    topic=msg.topic,
                    payload=payload,
                    qos=msg.qos)
            except:
                log.error(self.__LOG_OUTBOUND_MSG_SENDER,
                          msg=f'Error in outbound message sender task. '
                              f'Traceback = {traceback.print_exc()}')