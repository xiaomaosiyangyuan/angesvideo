VALID_NUM_FRAMES = {8 * n + 1 for n in range(1, 56)}

MIN_FRAME_RATE = 1
MAX_FRAME_RATE = 60

DEFAULT_POLL_INTERVAL = 5
DEFAULT_MAX_RETRIES = 3
DEFAULT_OUTPUT_DIR = "./output"
DEFAULT_LOG_FILE = "./batch.log"
DEFAULT_KEY_FILE = "./key.txt"

MAX_FRAMES = 441
MIN_FRAMES = 9

DOWNLOAD_RETRIES = 2
DOWNLOAD_RETRY_DELAY = 5

IMAGE_MODEL = "agnes-image-2.0-flash"
DEFAULT_IMAGE_SIZE = "1152x768"

FFMPEG_PATH = r"C:\Users\Administrator\AppData\Local\Programs\Python\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"