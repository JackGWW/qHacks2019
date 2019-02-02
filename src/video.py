from utils import detector_utils as detector_utils
import cv2
import tensorflow as tf
import multiprocessing
from multiprocessing import Queue, Pool, Value
import time
from utils.detector_utils import WebcamVideoStream
import datetime
import argparse

frame_processed = 0
score_thresh = 0.2

# Create a worker thread that loads graph and
# does detection on images in an input queue and puts it on an output queue

def calculate_movement(old, cur):
    # TODO - normalize for video resolution
    if old is None:
        return 0

    xmov = abs(old[0] - cur[0])
    ymov = abs(old[1] - cur[1])
    return xmov + ymov


def worker(input_q, output_q, cap_params, frame_processed, movement, movement_threshold):
    print(">> loading frozen model for worker")
    detection_graph, sess = detector_utils.load_inference_graph()
    sess = tf.Session(graph=detection_graph)
    old_centers = [None] * cap_params["num_hands_detect"]
    centers = [None] * cap_params["num_hands_detect"]
    while True:
        #print("> ===== in worker loop, frame ", frame_processed)
        frame = input_q.get()
        if (frame is not None):
            # Actual detection. Variable boxes contains the bounding box cordinates for hands detected,
            # while scores contains the confidence for each of these boxes.
            # Hint: If len(boxes) > 1 , you may assume you have found atleast one hand (within your score threshold)

            boxes, scores = detector_utils.detect_objects(
                frame, detection_graph, sess)

            # draw bounding boxes
            if any(centers):
                # If both hands detected
                if all(old_centers) and all(centers):
                    moved1 = calculate_movement(old_centers[0], centers[0])
                    moved2 = calculate_movement(old_centers[1], centers[0])
                    moved = min(moved1, moved2)

                # Try to match hand movement to closest hand postion before
                else:
                    moved1 = calculate_movement(old_centers[0], centers[0])
                    
                    if old_centers[1]:
                        moved2 = calculate_movement(old_centers[1], centers[0])
                    else:
                        moved2 = 99999
                    
                    if centers[1]:
                        moved3 = calculate_movement(old_centers[0], centers[1])
                    else:
                        moved3 = 99999

                    moved = min(moved1, moved2, moved3)

                if moved > movement_threshold:
                    # moved = 0
                    pass

                with movement.get_lock():
                    movement.value += moved
                
                old_centers = centers
            
            centers = detector_utils.draw_box_on_image(
                      cap_params["num_hands_detect"], cap_params["score_thresh"],
                      scores, boxes, cap_params['im_width'], cap_params['im_height'],
                      frame)


            # add frame annotated with bounding box to queue
            output_q.put(frame)
            frame_processed += 1
        else:
            output_q.put(frame)
    sess.close()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-src',
        '--source',
        dest='video_source',
        type=int,
        default=0,
        help='Device index of the camera.')
    parser.add_argument(
        '-nhands',
        '--num_hands',
        dest='num_hands',
        type=int,
        default=2,
        help='Max number of hands to detect.')
    parser.add_argument(
        '-fps',
        '--fps',
        dest='fps',
        type=int,
        default=1,
        help='Show FPS on detection/display visualization')
    parser.add_argument(
        '-wd',
        '--width',
        dest='width',
        type=int,
        default=300,
        help='Width of the frames in the video stream.')
    parser.add_argument(
        '-ht',
        '--height',
        dest='height',
        type=int,
        default=200,
        help='Height of the frames in the video stream.')
    parser.add_argument(
        '-ds',
        '--display',
        dest='display',
        type=int,
        default=1,
        help='Display the detected images using OpenCV. This reduces FPS')
    parser.add_argument(
        '-num-w',
        '--num-workers',
        dest='num_workers',
        type=int,
        default=4,
        help='Number of workers.')
    parser.add_argument(
        '-q-size',
        '--queue-size',
        dest='queue_size',
        type=int,
        default=5,
        help='Size of the queue.')
    args = parser.parse_args()

    input_q = Queue(maxsize=args.queue_size)
    output_q = Queue(maxsize=args.queue_size)

    video_capture = WebcamVideoStream(
        src=args.video_source, width=args.width, height=args.height).start()

    cap_params = {}
    frame_processed = 0
    cap_params['im_width'], cap_params['im_height'] = video_capture.size()
    cap_params['score_thresh'] = score_thresh

    # max number of hands we want to detect/track
    cap_params['num_hands_detect'] = args.num_hands

    print(cap_params, args)

    movement = Value('i', 0)
    movement_threshold = (args.width + args.height) / 3

    # spin up workers to paralleize detection.
    pool = Pool(args.num_workers, worker,
                (input_q, output_q, cap_params, frame_processed, movement, movement_threshold))

    start_time = datetime.datetime.now()
    num_frames = 0
    fps = 0
    index = 0
    old_movement = 0
    history_avg = 4
    move_history = [0] * history_avg 
    total_space = args.width + args.height

    cv2.namedWindow('Multi-Threaded Detection', cv2.WINDOW_NORMAL)

    while True:
        frame = video_capture.read()
        frame = cv2.flip(frame, 1)
        index += 1

        input_q.put(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        output_frame = output_q.get()

        output_frame = cv2.cvtColor(output_frame, cv2.COLOR_RGB2BGR)

        elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
        num_frames += 1
        fps = num_frames / elapsed_time

        # Calculate amount moved in the last 5 frames
        frame_rate = 5
        if num_frames % frame_rate == 0:
            cur_movement = movement.value
            moved = (cur_movement - old_movement) / frame_rate
            old_movement = cur_movement
            
            # Track historical movement
            move_history.append(moved)
            
            total = 0
            for i in range(len(move_history)-history_avg, len(move_history)):
                total += move_history[i]
            
            moved_avg = ((total / history_avg) / total_space) * 1000 
            print("Movement score: {}".format(moved_avg))

        # print("frame ",  index, num_frames, elapsed_time, fps)
        if (output_frame is not None):
            if (args.display > 0):
                if (args.fps > 0):
                    detector_utils.draw_fps_on_image("FPS : " + str(int(fps)),
                                                     output_frame)
                cv2.imshow('Multi-Threaded Detection', output_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                if (num_frames == 400):
                    num_frames = 0
                    start_time = datetime.datetime.now()
                else:
                    print("frames processed: ", index, "elapsed time: ",
                          elapsed_time, "fps: ", str(int(fps)))
        else:
            # print("video end")
            break
    elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
    fps = num_frames / elapsed_time
    print("fps", fps)
    pool.terminate()
    video_capture.stop()
    cv2.destroyAllWindows()
