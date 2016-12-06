import struct
from enum import Enum

HEADER_FORMAT = '!Bi'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


# Access the value by calling MessageTypes.--type--.value
# e.g. MessageTypes.SUBSCRIBE_MESSAGE.value
class MessageTypes(Enum):
    # format: 
    SUBSCRIBE_MESSAGE = 1  # Sent by client to subscribe
    # [SUBSCRIBE_MESSAGE]
    # Server responses:
        # [SUBSCRIBE_ACK_MESSAGE][ClientID], where ClientID is autogenerated by server
        # [ERROR][TOO_MANY_CLIENTS], error code where client is unable to subscribe
    SUBSCRIBE_ACK_MESSAGE = 2  # Sent by server to ack subscribe
    # [SUBSCRIBE_ACK_MESSAGE][ClientID], where ClientID is autogenerated by server
    RESUBSCRIBE_MESSAGE = 3 # Sent by client that was temporarily disconnected to reconnect
    # [RESUBSCRIBE_MESSAGE][ClientID]
    # Server responses:
        # [SUBSCRIBE_ACK_MESSAGE][ClientID]
        # [ERROR][NAME_ACTIVE], sent by server to client that is resubscribing to a name it considers actively connected
        # [ERROR][TOO_MANY_CLIENTS], sent by server if it already has enough clients
    JOB_READY = 4  # Sent by server to tell client a job is ready
    # [JOB_READY][JobID], JobID unique to job
    JOB_READY_TO_RECEIVE = 5  # Sent by client to acknowledge job ready, ready to receive job
    # [JOB_READY_TO_RECEIVE][ClientID][JobID], ACKs job ID
    JOB_INSTRUCTIONS_FILE = 6
    JOB_INSTRUCTIONS_FILE_ACK = 7
    DATAFILE = 8 # Sent by server to client to give it the data for the current job
    # [DATAFILE][ClientID][Filename][SeqNo]
    # Client is responsible for writing the data to a file in order
    DATAFILE_ACK = 9 # Sent by client to server to ACK  data
    # [DATAFILE_ACK][ClientID][Filename][SeqNo]
    # Server can move on to next file when current file is done sending
    JOB_START = 10 # Sent by server to client to tell client to begin job
    # [JOB_START][ClientID][JobID]
    # If client does not have data for current job it will send an error
    JOB_START_ACK = 11 # Sent by client to server to notify job has begun
    # [JOB_START_ACK][ClientID][JobID]
    JOB_HEARTBEAT = 12 # Sent by client to server to periodically update server on job progress for client
    # [JOB_HEARTBEAT][ClientID][JobID][Phase][SeqNo]
    # Phase is Mapper or Reducer
    # SeqNo is heartbeat #
    # Server logic should track rate of client
    JOB_DONE = 13
    JOB_DONE_ACK = 14

    # Command messages
    SUBMIT_JOB = 15  # Commander sends to server w/ mapper, reducer, data paths
    SUBMIT_JOB_ACK = 16  # Server acks the command
    SUBMITTED_JOB_FINISHED = 17  # Server announces completion w/ data path
    SUBMITTED_JOB_FINISHED_ACK = 18  # Commander acks completion

    SERVER_ERROR = 98
    # [SERVER_ERROR][ERROR_CODE]
    # Error can mean a variety of things, it is up to the error handler to interpret the error code
    CLIENT_ERROR = 99
    # [CLIENT_ERROR][ClientID][ERROR_CODE]
    # Additionally specified is the client ID


class Message(object):
    def __init__(self, m_type, body=None):
        self.m_type = m_type
        self._body = body  # body must be a string or there will be errors

    def __str__(self):
        return '<Message: type={m_type} body={body}>'.format(m_type=self.m_type, body=self._body)

    def has_body(self):
        return self._body

    def get_header_for_send(self):
        return struct.pack(HEADER_FORMAT, self.m_type.value, len(self._body) if self._body else 0)

    def get_body_for_send(self):
        return struct.pack(str(len(self._body)) + 's', bytes(self._body, encoding='utf-8'))

    def is_type(self, m_type):
        return m_type is self.m_type

    def get_body(self):
        """
        Get body of received message
        :return:
        """
        return str(self._body, encoding='utf-8')


class SubscribeMessage(Message):
    def __init__(self):
        super().__init__(MessageTypes.SUBSCRIBE_MESSAGE)


class SubscribeAckMessage(Message):
    def __init__(self):
        super().__init__(MessageTypes.SUBSCRIBE_ACK_MESSAGE)


class JobReadyMessage(Message):
    def __init__(self, job_id):
        super().__init__(MessageTypes.JOB_READY, job_id)


class JobReadyToReceiveMessage(Message):
    def __init__(self):
        super().__init__(MessageTypes.JOB_READY_TO_RECEIVE)


class JobStartAckMessage(Message):
    def __init__(self):
        super().__init__(MessageTypes.JOB_START_ACK)


class JobInstructionsFileMessage(Message):
    separator = ';;'

    def __init__(self, path, type, num_workers, partition_num):
        super().__init__(MessageTypes.JOB_INSTRUCTIONS_FILE,
                         '{path};;{type};;{num_workers};;{partition_num}'.format(
                             path=path,
                             type=type,
                             num_workers=num_workers,
                             partition_num=partition_num
                         ))

    @staticmethod
    def get_path_from_message(message):
        return message.get_body().split(JobInstructionsFileMessage.separator)[0]

    @staticmethod
    def get_type_from_message(message):
        return message.get_body().split(JobInstructionsFileMessage.separator)[1]

    @staticmethod
    def get_num_workers_from_message(message):
        return int(message.get_body().split(JobInstructionsFileMessage.separator)[2])

    @staticmethod
    def get_partition_num_from_message(message):
        return int(message.get_body().split(JobInstructionsFileMessage.separator)[3])


class JobInstructionsFileAckMessage(Message):
    def __init__(self):
        super().__init__(MessageTypes.JOB_INSTRUCTIONS_FILE_ACK)


class DataFileMessage(Message):
    def __init__(self, path):
        super().__init__(MessageTypes.DATAFILE, path)


class DataFileAckMessage(Message):
    def __init__(self):
        super().__init__(MessageTypes.DATAFILE_ACK)


class JobStartMessage(Message):
    def __init__(self):
        super().__init__(MessageTypes.JOB_START)


class JobDoneMessage(Message):
    def __init__(self, path):
        super().__init__(MessageTypes.JOB_DONE, path)


class JobDoneAckMessage(Message):
    def __init__(self):
        super().__init__(MessageTypes.JOB_DONE_ACK)


class SubmitJobMessage(Message):
    separator = ';;'

    def __init__(self, mapper_name, reducer_name, data_file_path):
        super().__init__(
            MessageTypes.SUBMIT_JOB,
            body=SubmitJobMessage.separator.join([mapper_name, reducer_name, data_file_path])
        )

    @staticmethod
    def get_mapper_name(message):
        return message.get_body().split(SubmitJobMessage.separator)[0]

    @staticmethod
    def get_reducer_name(message):
        return message.get_body().split(SubmitJobMessage.separator)[1]

    @staticmethod
    def get_data_file_path(message):
        return message.get_body().split(SubmitJobMessage.separator)[2]


class SubmitJobAckMessage(Message):
    def __init__(self):
        super().__init__(MessageTypes.SUBMIT_JOB_ACK)


class SubmittedJobFinishedMessage(Message):
    def __init__(self, data_file_path):
        super().__init__(MessageTypes.SUBMITTED_JOB_FINISHED, body=data_file_path)

    @staticmethod
    def get_data_file_path(message):
        return message.get_body()


class SubmittedJobFinishedAckMessage(Message):
    def __init__(self):
        super().__init__(MessageTypes.SUBMITTED_JOB_FINISHED_ACK)

class JobHeartbeatMessage(Message):
    separator = ';;'
    def __init__(self, progress, rate):
        super().__init__(MessageTypes.JOB_HEARTBEAT, 
            body=JobHeartbeatMessage.separator.join([progress, rate]))

    @staticmethod
    def get_progress(message):
        return message.get_body().split(JobHeartbeatMessage.separator)[0]

    @staticmethod
    def get_rate(message):
        return message.get_body().split(JobHeartbeatMessage.separator)[1]