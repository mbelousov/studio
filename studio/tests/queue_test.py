import unittest
import uuid
import os
import time
import logging


try:
    import boto3
except BaseException:
    boto3 = None


from studio.pubsub_queue import PubsubQueue
from studio.sqs_queue import SQSQueue

logging.basicConfig()


class QueueTest(object):
    def get_queue(self):
        pass

    def test_simple(self):
        q = self.get_queue()
        q.clean()
        data = str(uuid.uuid4())

        q.enqueue(data)
        recv_data = q.dequeue()

        self.assertEquals(data, recv_data)
        self.assertFalse(q.has_next())

    def test_clean(self):
        q = self.get_queue()
        q.clean()
        data = str(uuid.uuid4())

        q.enqueue(data)
        q.clean()

        self.assertFalse(q.has_next())

    # @skip
    def test_enq_deq_order(self):
        return
        q = self.get_queue()
        q.clean()
        data1 = str(uuid.uuid4())
        data2 = str(uuid.uuid4())

        q.enqueue(data1)
        # neither pubsub nor local queue are actually
        # very punctual about the order. This delay is
        # intended to ensure the messages are not
        # swapped accidentally
        time.sleep(1)
        q.enqueue(data2)

        recv_data1 = q.dequeue()
        recv_data2 = q.dequeue()

        self.assertEquals(data1, recv_data1)
        self.assertEquals(data2, recv_data2)

        self.assertFalse(q.has_next())


class DistributedQueueTest(QueueTest):
    _multiprocess_can_split_ = True

    def test_unacknowledged(self):
        q = self.get_queue()
        q.clean()
        data1 = str(uuid.uuid4())
        data2 = str(uuid.uuid4())

        q.enqueue(data1)
        q.enqueue(data2)

        recv1 = q.dequeue()
        time.sleep(15)
        recv2 = q.dequeue()

        self.assertTrue(data1 == recv1 or data2 == recv1)
        self.assertTrue(data1 == recv2 or data2 == recv2)
        self.assertFalse(recv1 == recv2)

        self.assertFalse(q.has_next())

    def test_two_receivers(self):
        logger = logging.getLogger('test_two_receivers')
        logger.setLevel(10)
        q1 = self.get_queue()
        q1.clean()

        q2 = self.get_queue(q1.get_name())

        data1 = str(uuid.uuid4())
        data2 = str(uuid.uuid4())

        logger.debug('data1 = ' + data1)
        logger.debug('data2 = ' + data2)

        q1.enqueue(data1)

        self.assertEquals(data1, q2.dequeue())

        q1.enqueue(data1)
        q1.enqueue(data2)

        recv1 = q1.dequeue()
        recv2 = q2.dequeue()

        logger.debug('recv1 = ' + recv1)
        logger.debug('recv2 = ' + recv2)

        self.assertTrue(data1 == recv1 or data2 == recv1)
        self.assertTrue(data1 == recv2 or data2 == recv2)
        self.assertFalse(recv1 == recv2)

        self.assertFalse(q1.has_next())
        self.assertFalse(q2.has_next())

    def test_hold(self):
        q = self.get_queue()
        q.clean()

        data = str(uuid.uuid4())
        q.enqueue(data)

        msg, ack_id = q.dequeue(acknowledge=False)

        self.assertFalse(q.has_next())
        q.hold(ack_id, 0.5)
        time.sleep(35)
        msg = q.dequeue()

        self.assertEquals(data, msg)


@unittest.skipIf(
    'GOOGLE_APPLICATION_CREDENTIALS' not in
    os.environ.keys(),
    'GOOGLE_APPLICATION_CREDENTIALS environment ' +
    'variable not set, won'' be able to use google ' +
    'PubSub')
class PubSubQueueTest(DistributedQueueTest, unittest.TestCase):
    _multiprocess_can_split_ = True

    def get_queue(self, name=None):
        return PubsubQueue(
            'pubsub_queue_test_' + str(uuid.uuid4()) if not name else name)


@unittest.skipIf(
    boto3 is None,
    "boto3 is not present, cannot use SQSQueue")
class SQSQueueTest(DistributedQueueTest, unittest.TestCase):
    _multiprocess_can_split_ = True

    def get_queue(self, name=None):
        return SQSQueue(
            'sqs_queue_test_' + str(uuid.uuid4()) if not name else name)


if __name__ == '__main__':
    unittest.main()
