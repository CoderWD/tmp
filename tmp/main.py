from yt_dlp import YoutubeDL
from yt_dlp.globals import plugin_dirs
import os
import sys
import json
import re
import tempfile


def extractor_exception_json(url, err_msg):
    """与 Swift ExtractorException(url:errMsg:) 对应的 JSON 字符串。"""
    return json.dumps({"url": url or "", "errMsg": str(err_msg)}, ensure_ascii=False)


def make_cache_dir(library_path):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if not library_path:
        cache_dir = os.path.join(current_dir, ".cache")
    else:
        cache_dir = os.path.join(library_path, ".cache")

    # 判断目录是否存在
    if not os.path.exists(cache_dir):
        # 如果目录不存在，创建目录
        os.makedirs(cache_dir)
        # 设置权限为可读写（仅当前用户）
        os.chmod(cache_dir, 0o700)
        print(f"cache dir '{cache_dir}' created.")
    else:
        print(f"cache dir '{cache_dir}' already exists.")

    return cache_dir


def create_cookies_file(cookie_str, cache_dir):
    """
    创建临时 cookies 文件用于 yt-dlp
    参数:
        cookie_str: Netscape 格式的 cookie 字符串
        cache_dir: 缓存目录路径
    返回:
        cookies 文件路径，如果失败返回 None
    """
    # 检查输入是否为空
    if not cookie_str.strip():
        print("Cookie 字符串为空")
        return None

    lines = cookie_str.strip().splitlines()

    # 检查是否为有效的 Netscape 格式
    if len(lines) < 2:
        print("Cookie 格式无效：行数不足")
        return None

    # 检查第一行是否为 Netscape 头部
    if lines[0].strip() != "# Netscape HTTP Cookie File":
        print("Cookie 格式无效：缺少 Netscape 头部")
        return None

    try:
        # 创建 cookies 文件路径
        cookies_file_path = os.path.join(cache_dir, "cookies.txt")

        # 写入 cookies 文件
        with open(cookies_file_path, 'w', encoding='utf-8') as f:
            f.write(cookie_str)

        print(f"Cookies 文件已创建: {cookies_file_path}")
        return cookies_file_path

    except Exception as e:
        print(f"创建 cookies 文件失败: {e}")
        return None


def process_cookie(cookie_str):
    """
    保留原有的处理方法作为备用（已废弃使用）
    """
    # 检查输入是否为空或只有一行
    if not cookie_str.strip() or len(cookie_str.splitlines()) <= 1:
        return ""  # 输出空字符串
    else:
        # 分割字符串为行，忽略第一行
        lines = cookie_str.splitlines()[1:]

        # 初始化 cookie 字符串
        cookie_string = ""

        # 遍历每一行并提取 key 和 value
        for line in lines:
            parts = line.split("\t")
            if len(parts) >= 3:  # 保证有至少 3 个部分
                key = parts[-2]  # 倒数第二个是 key
                value = parts[-1]  # 倒数第一个是 value
                cookie_string += f"{key}={value}; "

        # 去掉最后一个多余的分号和空格
        cookie_string = cookie_string.strip("; ")
        return cookie_string


def isCookieLangEnRegion(cookie_string_or_file):
    """
    检查 cookies 中是否设置了英文区域
    参数:
        cookie_string_or_file: cookie 字符串或 Netscape 格式的 cookie 内容
    """
    cookie_content = ""

    # 如果输入为空，返回 False
    if not cookie_string_or_file:
        return False

    # 判断是否为 Netscape 格式（多行且包含头部）
    if '\n' in cookie_string_or_file and "# Netscape HTTP Cookie File" in cookie_string_or_file:
        # 解析 Netscape 格式
        lines = cookie_string_or_file.strip().splitlines()
        for line in lines:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split('\t')
            if len(parts) >= 6:  # Netscape 格式至少有 6 列
                name = parts[5] if len(parts) > 5 else parts[-2]
                value = parts[6] if len(parts) > 6 else parts[-1]
                if name == 'custom_lang':
                    return value.startswith('en')
    else:
        # 当作普通 cookie 字符串处理
        cookies = cookie_string_or_file.split(';')
        for cookie in cookies:
            cookie = cookie.strip()  # 移除空白字符
            if cookie.startswith('custom_lang='):
                # 提取语言值
                lang_value = cookie[12:]  # 去掉 'custom_lang=' 前缀
                # 检查是否以 'en' 开头
                return lang_value.startswith('en')

    return False


def read_language_cache():
    # 获取当前文件所在的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, ".cache_lang")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            print(f'lang cache is: {content}')
        return content
    except FileNotFoundError:
        print(".cache_lang not exists")
        return None
    except Exception as e:
        print(f'read language cache error: {str(e)}')
        return None

def compare_version(version1, version2):
    """
    # 测试
    test_versions = ["1.4.0", "1.3.3", "1.3.2", "1.3.1", "1.2.9", "2.0.0", "1.3"]
    for v in test_versions:
        result = compare_version(v, "1.3.2")
        status = "大于" if result > 0 else "等于" if result == 0 else "小于"
        print(f"{v:6} {status} 1.3.2")
    """
    """
    比较两个版本号
    返回值：1 表示 version1 > version2
           0 表示 version1 = version2
          -1 表示 version1 < version2
    """
    def normalize_version(v):
        return [int(x) for x in v.split('.')]

    v1_parts = normalize_version(version1)
    v2_parts = normalize_version(version2)

    # 补齐长度，短的版本号后面补0
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))

    if v1_parts > v2_parts:
        return 1
    elif v1_parts < v2_parts:
        return -1
    else:
        return 0


def is_m3u8_format(format_dict) -> bool:
    """
    判断是否为 m3u8 格式

    判断标准：
    1. protocol 为 'm3u8_native'
    2. 或者 url 中包含 '.m3u8'
    3. 或者 manifest_url 存在（m3u8 格式通常有 manifest_url）
    """
    protocol = format_dict.get('protocol', '')
    url = format_dict.get('url', '')
    manifest_url = format_dict.get('manifest_url', '')

    # 方法1: 检查 protocol
    if protocol == 'm3u8_native':
        return True

    # 方法2: 检查 URL 中是否包含 .m3u8
    if '.m3u8' in url or '.m3u8' in manifest_url:
        return True

    # 方法3: 检查是否有 manifest_url（m3u8 格式通常有这个字段）
    # if manifest_url:
    #     return True

    return False


def is_video_format(format_dict) -> bool:
    """
    简单判断是否为视频格式（不排除 m3u8）
    判断标准：vcodec 有值（不管 acodec 是什么）
    这样可以识别纯视频流和音视频混合格式（如 m3u8）
    """
    vcodec = format_dict.get('vcodec', 'none')
    # vcodec 有值就是视频格式（包括音视频混合格式）
    return vcodec != 'none' and vcodec is not None


def filter_m3u8_from_video_formats(info_dict):
    """
    过滤掉视频格式里的 m3u8，其他所有格式保留

    逻辑：
    1. 如果是视频格式且是 m3u8，则过滤掉
    2. 其他格式（音频、storyboard、非 m3u8 视频等）都保留
    3. 判断剩下的格式里是否还有视频格式
    4. 如果没有视频格式了，返回原来的 format 数组
    """
    formats = info_dict['formats']
    # 过滤：只过滤掉视频格式中的 m3u8
    filtered = []
    for f in formats:
        # 如果是视频格式且是 m3u8，则跳过（过滤掉）
        if is_video_format(f) and is_m3u8_format(f):
            continue
        # 其他格式都保留
        filtered.append(f)

    # 判断剩下的格式里是否还有视频格式
    has_video = any(is_video_format(f) for f in filtered)

    if has_video:
        info_dict['formats'] = filtered

    return info_dict


SEARCH_PREFIX_MAP = {
    'youtube': 'ytsearch',
    'soundcloud': 'scsearch',
}


def _setup_python_paths_and_plugins(version):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for root, dirs, files in os.walk(current_dir):
        if root not in sys.path:
            sys.path.append(root)
    if compare_version(version, "1.3.12") > 0:
        plugin_dir = os.path.join(current_dir, "yt_dlp_plugins")
        plugin_dirs.value = [plugin_dir, 'default']


def _apply_cookies_to_ydl_opts(ydl_opts, cookie_str, cookies_file_path):
    if cookies_file_path:
        ydl_opts['cookiefile'] = cookies_file_path
        print(f"使用 cookies 文件: {cookies_file_path}")
    else:
        print("警告: 无法创建 cookies 文件，将不使用 cookies")
        cookie_string = process_cookie(cookie_str)
        if cookie_string:
            ydl_opts['http_headers'] = {'Cookie': cookie_string}
            print("备用方案：使用 http_headers 传递 cookies")


def _upgrade_thumbnail_url(url, entry=None):
    if not url or not isinstance(url, str):
        return url
    if 'sndcdn.com' in url:
        url = re.sub(r'-t\d+x\d+\.', '-t500x500.', url)
        url = re.sub(r'-(?:large|small|badge|tiny|mini)\.', '-t500x500.', url)
        return url
    if 'ytimg.com' in url or (entry and entry.get('ie_key') == 'Youtube'):
        video_id = None
        if entry:
            raw_id = entry.get('id')
            if isinstance(raw_id, str) and len(raw_id) == 11 and ' ' not in raw_id:
                video_id = raw_id
        if not video_id:
            match = re.search(r'/vi/([^/]+)/', url)
            video_id = match.group(1) if match else None
        if video_id:
            return f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'
    return url


def _pick_thumbnail(entry):
    thumbs = entry.get('thumbnails') or []
    candidates = []
    if isinstance(thumbs, list):
        for thumb_item in thumbs:
            if not isinstance(thumb_item, dict):
                continue
            thumb_url = thumb_item.get('url')
            if not thumb_url:
                continue
            width = thumb_item.get('width') or 0
            height = thumb_item.get('height') or 0
            candidates.append((width * height, thumb_url))

    single = entry.get('thumbnail')
    if single:
        candidates.append((0, single))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return _upgrade_thumbnail_url(candidates[0][1], entry)


def _normalize_search_entry(entry):
    if not entry or not isinstance(entry, dict):
        return None
    entry_id = entry.get('id')
    webpage_url = entry.get('webpage_url') or entry.get('url')
    if not webpage_url and entry_id:
        if isinstance(entry_id, str) and entry_id.startswith('http'):
            webpage_url = entry_id
        elif entry.get('ie_key') == 'Youtube':
            webpage_url = f"https://www.youtube.com/watch?v={entry_id}"
    if not webpage_url:
        return None
    return {
        'id': entry_id,
        'title': entry.get('title') or entry.get('fulltitle') or '',
        'url': webpage_url,
        'webpage_url': webpage_url,
        'thumbnail': _pick_thumbnail(entry),
        'duration': entry.get('duration'),
        'uploader': entry.get('uploader') or entry.get('channel') or entry.get('uploader_id'),
        'view_count': entry.get('view_count'),
    }


def search(query, cookie_str, json_param_str, library_path, version="1.3.12"):
    """yt-dlp 站点搜索，返回 entries 列表 JSON。"""
    print(f"search from python: {query}")
    print(f"param: {json_param_str}")
    cookies_file_path = None
    try:
        if not query or not str(query).strip():
            return extractor_exception_json(query or "", "Search query is empty")

        limit = 20
        search_type = 'youtube'
        if json_param_str:
            try:
                params = json.loads(json_param_str)
                limit = int(params.get('limit', limit))
                search_type = str(params.get('type', search_type)).lower()
            except Exception as parse_error:
                print(f"search param parse warning: {parse_error}")

        limit = max(1, min(limit, 50))
        prefix = SEARCH_PREFIX_MAP.get(search_type, 'ytsearch')
        search_url = f"{prefix}{limit}:{query.strip()}"

        _setup_python_paths_and_plugins(version)
        cache_dir = make_cache_dir(library_path)
        cookies_file_path = create_cookies_file(cookie_str, cache_dir)

        ydl_opts = {
            'socket_timeout': 20,
            'quiet': True,
            'dumpjson': True,
            'cachedir': cache_dir,
            'noplaylist': False,
            'extract_flat': 'in_playlist',
            'remote_components': ['ejs:github'],
        }
        _apply_cookies_to_ydl_opts(ydl_opts, cookie_str, cookies_file_path)

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(search_url, download=False)

        entries = []
        if info_dict:
            raw_entries = info_dict.get('entries') or []
            for entry in raw_entries:
                normalized = _normalize_search_entry(entry)
                if normalized and normalized.get('title'):
                    entries.append(normalized)

        result = {
            'query': query.strip(),
            'search_type': search_type,
            'entries': entries,
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        print(f"search error: {e}")
        return extractor_exception_json(query or "", str(e))
    finally:
        if cookies_file_path and os.path.exists(cookies_file_path):
            try:
                os.remove(cookies_file_path)
            except Exception as cleanup_error:
                print(f"清理 cookies 文件失败: {cleanup_error}")


def extract(url, cookie_str, json_param_str, library_path, version="1.3.12"):
    print(f"extract from python: {url}")
    print(f"param: {json_param_str}")
    print(f"cookie: {cookie_str}")
    print(f"version: {version}")
    result = ""
    try:
        _setup_python_paths_and_plugins(version)
        cache_dir = make_cache_dir(library_path)

        # 创建 cookies 文件
        cookies_file_path = create_cookies_file(cookie_str, cache_dir)

        # 判断是否为 YouTube URL
        if isYoutubeUrl(url):
            result = extractYoutube(url, cookie_str, json_param_str, library_path, cache_dir, cookies_file_path)
        else:
            result = extractCommon(url, cookie_str, json_param_str, library_path, cache_dir, cookies_file_path)

    except Exception as e:
        print(f"Error: {e}")
        return extractor_exception_json(url, str(e))
    finally:
        # 清理临时 cookies 文件（在外层统一处理）
        if 'cookies_file_path' in locals() and cookies_file_path and os.path.exists(cookies_file_path):
            try:
                os.remove(cookies_file_path)
                print(f"清理临时 cookies 文件: {cookies_file_path}")
            except Exception as cleanup_error:
                print(f"清理 cookies 文件失败: {cleanup_error}")

    return result


def isYoutubeUrl(url):
    """
    判断 URL 是否为 YouTube 链接

    Args:
        url: 要检查的 URL 字符串

    Returns:
        bool: 如果是 YouTube 链接返回 True，否则返回 False
    """
    if not url or not isinstance(url, str):
        return False

    # YouTube URL 模式（简化版，基于 yt-dlp 的 _VALID_URL）
    youtube_patterns = [
        r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)',
        r'https?://(?:m\.|music\.)?youtube\.com',
        r'https?://youtube\.googleapis\.com',
        r'youtube\.com/watch',
        r'youtu\.be/',
    ]

    url_lower = url.lower().strip()
    for pattern in youtube_patterns:
        if re.search(pattern, url_lower):
            return True

    return False


def extractYoutube(url, cookie_str, json_param_str, library_path, cache_dir, cookies_file_path):
    """
    提取 YouTube 视频信息

    Args:
        url: YouTube 视频 URL
        cookie_str: Cookie 字符串
        json_param_str: JSON 参数字符串
        library_path: 库路径
        cache_dir: 缓存目录
        cookies_file_path: Cookies 文件路径（由外层创建）

    Returns:
        str: JSON 格式的视频信息
    """
    result = ""

    try:

        # 15秒超时时间
        socket_timeout = 15

        format_selector = (
            "bv*[width<=1080]"
            "[protocol!=m3u8_native][protocol!=m3u8][protocol!=http_dash_segments]"
            "[protocol!=f4m][protocol!=ism]"
            "+ba[protocol!=m3u8_native][protocol!=m3u8][protocol!=http_dash_segments]"
            "[protocol!=f4m][protocol!=ism]"
        )

        # 配置下载选项，只解析不下载
        ydl_opts = {
            'socket_timeout': socket_timeout,
            'format': format_selector,
            # 'verbose': True,
            'quiet': True,  # 禁用其他输出
            'dumpjson': True,  # 输出解析后的 JSON 数据
            'cachedir': cache_dir,  # 设置缓存目录为当前脚本所在目录
            'noplaylist': True,  # 仅处理单个视频，不处理播放列表
            'remote_components': ['ejs:github']
            # 'js_runtimes': {'node': {'path': None}},  # 字典格式，设置 node 运行时路径为 None，使用系统默认路径; 由于使用了自定义插件调用本地服务，暂时不需要这个 runtime
        }
        print(f'ydl_opts: {ydl_opts}')
        # 如果成功创建了 cookies 文件，则添加到配置中
        if cookies_file_path:
            ydl_opts['cookiefile'] = cookies_file_path
            print(f"使用 cookies 文件: {cookies_file_path}")
        else:
            print("警告: 无法创建 cookies 文件，将不使用 cookies")
            # 作为备用方案，仍然使用旧的方法
            cookie_string = process_cookie(cookie_str)
            if cookie_string:
                ydl_opts['http_headers'] = {
                    'Cookie': cookie_string,
                }
                print(f"备用方案：使用 http_headers 传递 cookies")

        # 检查是否为英文区域
        is_english_region = isCookieLangEnRegion(cookie_str)

        # 执行解析，获取下载链接
        with YoutubeDL(ydl_opts) as ydl:
            try:
                info_dict = ydl.extract_info(url, download=False)  # 提取信息而不下载
                # 输出所有格式的下载链接
                result = json.dumps(info_dict, indent=4)
                if info_dict and 'formats' in info_dict:
                    for format_info in info_dict['formats']:
                        print(format_info)

            except Exception as e:
                print(f"An error occurred: {e}")
                return extractor_exception_json(url, str(e))

    except Exception as e:
        print(f"Error in extractYoutube: {e}")
        return extractor_exception_json(url, str(e))

    return result


def extractCommon(url, cookie_str, json_param_str, library_path, cache_dir, cookies_file_path):
    result = ""
    try:
        # 15秒超时时间
        socket_timeout = 15
        format_selector = (
            "bv*[width<=1080]"
            "[protocol!=m3u8_native][protocol!=m3u8][protocol!=http_dash_segments]"
            "[protocol!=f4m][protocol!=ism]"
            "+ba[protocol!=m3u8_native][protocol!=m3u8][protocol!=http_dash_segments]"
            "[protocol!=f4m][protocol!=ism]"
        )

        # 配置下载选项，只解析不下载
        ydl_opts = {
            'socket_timeout': socket_timeout,
            # 'format': format_selector,
            # 'verbose': True,
            'quiet': True,  # 禁用其他输出
            'dumpjson': True,  # 输出解析后的 JSON 数据
            'cachedir': cache_dir,  # 设置缓存目录为当前脚本所在目录
            'noplaylist': True,  # 仅处理单个视频，不处理播放列表
            'remote_components': ['ejs:github'],
            # 'ignoreerrors': True  # 忽略下载和后处理错误，下载将被视为成功
        }
        print(f'ydl_opts: {ydl_opts}')
        # 如果成功创建了 cookies 文件，则添加到配置中
        if cookies_file_path:
            ydl_opts['cookiefile'] = cookies_file_path
            print(f"使用 cookies 文件: {cookies_file_path}")
        else:
            print("警告: 无法创建 cookies 文件，将不使用 cookies")
            # 作为备用方案，仍然使用旧的方法
            cookie_string = process_cookie(cookie_str)
            if cookie_string:
                ydl_opts['http_headers'] = {
                    'Cookie': cookie_string,
                }
                print(f"备用方案：使用 http_headers 传递 cookies")

        # 执行解析，获取下载链接
        with YoutubeDL(ydl_opts) as ydl:
            try:
                info_dict = ydl.extract_info(url, download=False)  # 提取信息而不下载
                # 输出所有格式的下载链接
                result = json.dumps(info_dict, indent=4)
                if info_dict and 'formats' in info_dict:
                    for format_info in info_dict['formats']:
                        print(format_info)

            except Exception as e:
                print(f"An error occurred: {e}")
                return extractor_exception_json(url, str(e))

    except Exception as e:
        print(f"Error in extractCommon: {e}")
        return extractor_exception_json(url, str(e))

    return result


if __name__ == '__main__':
    url = "https://www.youtube.com/watch?v=T4SimnaiktU"
    url = "https://soundcloud.com/eva-ruiz-official/santa-cruz?in=soundcloud-la-onda/sets/fresco-emerging-latin-music&si=881ded650085437e954a8bd9287cd6ed&utm_source=clipboard&utm_medium=text&utm_campaign=social_sharing"
    # 测试用的 Netscape 格式 cookie 字符串（示例）
    cookie_str = """# Netscape HTTP Cookie File
.soundcloud.com	TRUE	/	FALSE	1804997819	sc_anonymous_id	404504-74004-854673-420383
.soundcloud.com	TRUE	/	TRUE	1801973829	datadome	lGp0RkxtI59gtt0lJ_NLTgZp7TAMNq3NG7hl6hd3tBVYfaCpQ5dmqlANpWiVKY9lhWC0ZekFkhFHi~PCjWtW7nEYjLSyAnfOV5cPntQIh7XSaME9FNwcH4wj8Y568K7j
.soundcloud.com	TRUE	/	TRUE	1801973818	OptanonConsent	isGpcEnabled=0&datestamp=Sat+Feb+07+2026+12%3A16%3A58+GMT%2B0800+(China+Standard+Time)&version=202502.1.0&browserGpcFlag=0&isIABGlobal=false&identifierType=Cookie+Unique+Id&hosts=&consentId=cacc8f29-8ccc-40d7-93e4-f44683563657&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1%2CV2STACK42%3A1&iType=1&intType=1&geolocation=JP%3B13&AwaitingReconsent=false
.soundcloud.com	TRUE	/	FALSE	1771042656	sc_session	{%22id%22:%228C6730E8-9C59-4629-9921-44DD874C1625%22%2C%22lastBecameInactive%22:%222026-02-07T04:17:36.239Z%22}
.soundcloud.com	TRUE	/	TRUE	1804997828	_ga_HXKL0JJB2D	GS2.1.s1770437820$o3$g1$t1770437828$j52$l0$h1858477572
.soundcloud.com	TRUE	/	TRUE	1804997828	_ga	GA1.1.1012779916.1770430218
.soundcloud.com	TRUE	/	TRUE	1801966220	OptanonAlertBoxClosed	2026-02-07T02:10:20.641Z
.soundcloud.com	TRUE	/	FALSE	1778206221	_gcl_au	1.1.1048000918.1770430221
.soundcloud.com	TRUE	/	TRUE	1801966220	eupubconsent-v2	CQfPKAAQfPKAAAcABBENCRFsAP_gAEPgAAYgL-tR_G__bWlr-bb3aftkeYxP9_hr7sQxBgbJk24FzLvW7JwXx2E5NAzatqIKmRIAu3TBIQNlHIDURUCgKIgFryDMaE2U4TNKJ6BkiFMZI2tYCFxvm4tjWQCY4vr99lc1mB-t7dr82dzyy6hHn3a5_2S1UJCdIYetDfv8ZBOT-9IEd_x8v4v4_EbpEm-eS1n_pGvp4jd-YnM_dBmxt-Tyff7Pn__rl_e7X_vc_n3zv94XH77v____fv-7___2b_-__-C_oAJhoVEEZZECAQKBhBAgAUFYQAUCAIAAEgaICAEwYEOQMAF1hMgBACgAGCAEAAIMAAQAACQAIRABAAQCAECAQKAAMACAICABgYAAwAWIgEAAIDoGKYEEAgWACRmVQaYEoACQQEtlQglAwIK4QhFngEECImCgAABAAKAABAeCwEJJASsSCALiCaAAAgAACiBEgRSFmAIKgzRaCsCTgMjTAMHzBMkp0GQBMEJGQZEJvwmHikKIUEOUGxSzAHTxBQAigAAA.f_wACHwAAAAA
.soundcloud.com	TRUE	/	FALSE	1804997820	afUserId	b50ff807-1042-40ad-bc84-1db546ec46f9-p
.soundcloud.com	TRUE	/	FALSE	1771035021	AF_SYNC	1770430221762
.soundcloud.com	TRUE	/	FALSE	1801973828	sc_tracking_anonymous_id	%2211d3acb0-a4e7-4612-ae91-fc4b38be662c%22
.soundcloud.com	TRUE	/	TRUE	1804997828	_ga_2MW685RTN1	GS2.1.s1770437828$o3$g0$t1770437828$j60$l0$h0"""
    # cookie_str = ""

    print("=== 测试新的 cookies 文件实现 ===")
    result = extract(url, cookie_str, "", None)
    if result:
        print(result)
        print("提取成功!")
    else:
        print("提取失败或无结果")
