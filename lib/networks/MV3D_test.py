import tensorflow as tf
from networks.network import Network

n_classes = 4
_feat_stride = [4,]
anchor_scales = [1, 1]

class MV3D_test(Network):
    def __init__(self, trainable=True):
        self.inputs = []
        self.lidar_bv_data = tf.placeholder(tf.float32, shape=[None, None, None, 24])
        self.image_data = tf.placeholder(tf.float32, shape=[None, None, None, 3])
        self.im_info = tf.placeholder(tf.float32, shape=[None, 3])
        self.gt_boxes = tf.placeholder(tf.float32, shape=[None, 5])
        self.gt_boxes_bv = tf.placeholder(tf.float32, shape=[None, 5])
        self.gt_boxes_3d = tf.placeholder(tf.float32, shape=[None, 7])
        self.gt_boxes_corners = tf.placeholder(tf.float32, shape=[None, 25])
        self.calib = tf.placeholder(tf.float32, shape=[None, 12])
        self.keep_prob = tf.placeholder(tf.float32)
        self.layers = dict({'lidar_bv_data':self.lidar_bv_data,
                            'image_data':self.image_data,
                            'calib' : self.calib,
                            'im_info':self.im_info,
                            'gt_boxes':self.gt_boxes,
                            'gt_boxes_bv':self.gt_boxes_bv,
                            'gt_boxes_3d': self.gt_boxes_3d,
                            'gt_boxes_corners': self.gt_boxes_corners})
        self.trainable = trainable
        self.setup()


    def setup(self):
        (self.feed('lidar_bv_data')
             .conv(3, 3, 64, 1, 1, name='conv1_1', trainable=False)
             .conv(3, 3, 64, 1, 1, name='conv1_2', trainable=False)
             .max_pool(2, 2, 2, 2, padding='VALID', name='pool1')
             .conv(3, 3, 128, 1, 1, name='conv2_1', trainable=False)
             .conv(3, 3, 128, 1, 1, name='conv2_2', trainable=False)
             .max_pool(2, 2, 2, 2, padding='VALID', name='pool2')
             .conv(3, 3, 256, 1, 1, name='conv3_1')
             .conv(3, 3, 256, 1, 1, name='conv3_2')
             .conv(3, 3, 256, 1, 1, name='conv3_3')
             .max_pool(2, 2, 2, 2, padding='VALID', name='pool3')
             .conv(3, 3, 512, 1, 1, name='conv4_1')
             .conv(3, 3, 512, 1, 1, name='conv4_2')
             .conv(3, 3, 512, 1, 1, name='conv4_3')
             .conv(3, 3, 512, 1, 1, name='conv5_1')
             .conv(3, 3, 512, 1, 1, name='conv5_2')
             .conv(3, 3, 512, 1, 1, name='conv5_3'))

        (self.feed('image_data')
              .conv(3, 3, 64, 1, 1, name='conv1_1_2', trainable=False)
              .conv(3, 3, 64, 1, 1, name='conv1_2_2', trainable=False)
              .max_pool(2, 2, 2, 2, padding='VALID', name='pool1_2')
              .conv(3, 3, 128, 1, 1, name='conv2_1_2', trainable=False)
              .conv(3, 3, 128, 1, 1, name='conv2_2_2', trainable=False)
              .max_pool(2, 2, 2, 2, padding='VALID', name='pool2_2')
              .conv(3, 3, 256, 1, 1, name='conv3_1_2')
              .conv(3, 3, 256, 1, 1, name='conv3_2_2')
              .conv(3, 3, 256, 1, 1, name='conv3_3_2')
              .max_pool(2, 2, 2, 2, padding='VALID', name='pool3_2')
              .conv(3, 3, 512, 1, 1, name='conv4_1_2')
              .conv(3, 3, 512, 1, 1, name='conv4_2_2')
              .conv(3, 3, 512, 1, 1, name='conv4_3_2')
              .conv(3, 3, 512, 1, 1, name='conv5_1_2')
              .conv(3, 3, 512, 1, 1, name='conv5_2_2')
              .conv(3, 3, 512, 1, 1, name='conv5_3_2'))

        #========= RPN ============
        (self.feed('conv5_3')
             .deconv(shape=None, c_o=512, stride=2, ksize=3,  name='deconv_2x_1')
             .conv(3,3,512,1,1,name='rpn_conv/3x3')
             .conv(1,1,len(anchor_scales)*2*2,1,1,padding='VALID',relu = False,name='rpn_cls_score'))

        (self.feed('rpn_conv/3x3')
             .conv(1,1,len(anchor_scales)*2*6,1,1,padding='VALID',relu = False,name='rpn_bbox_pred'))

        (self.feed('rpn_cls_score')
             .reshape_layer(2,name = 'rpn_cls_score_reshape')
             .softmax(name='rpn_cls_prob'))

        (self.feed('rpn_cls_prob')
             .reshape_layer(len(anchor_scales)*2*2,name = 'rpn_cls_prob_reshape'))

        (self.feed('rpn_cls_prob_reshape','rpn_bbox_pred','im_info','calib')
             .proposal_layer_3d(_feat_stride, 'TEST', name = 'rois'))

        (self.feed('rois')
             .proposal_transform(target='img', name='roi_data_img'))
        (self.feed('rois')
             .proposal_transform(target='bv', name='roi_data_bv'))


        # deconv
        (self.feed('conv5_3')
              .deconv(shape=None, c_o=512, stride=4, ksize=3, name='deconv_4x_1'))

        (self.feed('conv5_3_2')
              .deconv(shape=None, c_o=512, stride=2, ksize=3, name='deconv_2x_2'))

        #========= RoI Proposal ============
        # lidar_bv
        (self.feed('deconv_4x_1', 'rois')
             .roi_pool(7, 7, 1.0/2, name='pool_5')
             .fc(2048, name='fc6_1'))

        # image
        (self.feed('deconv_2x_2', 'rois')
             .roi_pool(7, 7, 1.0/4, name='pool_5')
             .fc(2048, name='fc6_2'))

        # fusion
        (self.feed('fc6_1', 'fc6_2')
             .concat(axis=1, name='concat1')
             .fc(4096, name='fc7')
             .fc(n_classes, relu=False, name='cls_score')
             .softmax(name='cls_prob'))

        (self.feed('fc7')
             .fc(n_classes*24, relu=False, name='bbox_pred')) # (x0-x7,y0-y7,z0-z7)
