from __future__ import annotations

import collections
import functools
import itertools
import json
import os
import typing
import urllib.parse
import json
import __main__

from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeProviderResponse,
    JsChallengeRequest,
    JsChallengeResponse,
    JsChallengeType,
    NChallengeOutput,
    SigChallengeOutput,
    register_provider,
)
from yt_dlp.networking import Request
from yt_dlp.networking.exceptions import HTTPError
from yt_dlp.utils import ExtractorError


@register_provider
class RemoteCipherJCP(JsChallengeProvider):
    PROVIDER_VERSION = '1.0.0'
    PROVIDER_NAME = 'remotecipher'
    REPO_URL = 'https://github.com/MCRicher/testEjs'
    BUG_REPORT_LOCATION = f'{REPO_URL}/issues'
    DEFAULT_SERVER_BASE_URL = 'http://localhost:8001'
    _SUPPORTED_TYPES = [JsChallengeType.N, JsChallengeType.SIG]

    def is_available(self) -> bool:
        return True

    @functools.cached_property
    def server_base_url(self) -> str:
        return self.DEFAULT_SERVER_BASE_URL

    @functools.cached_property
    def request_timeout(self) -> float | None:
        timeout = self._configuration_arg('timeout', default=[None])[0]
        if timeout is not None:
            self.logger.debug(f'Using provided request timeout: {timeout}')
            return float(timeout)
        return None

    def _flatten_challenges(self, requests: list[JsChallengeRequest]) -> tuple[list[tuple[JsChallengeRequest, str]], list[tuple[JsChallengeRequest, str]]]:
        flat_sig_items: list[tuple[JsChallengeRequest, str]] = []
        flat_n_items: list[tuple[JsChallengeRequest, str]] = []

        for req in requests:
            if req.type is JsChallengeType.SIG:
                for ch in req.input.challenges or []:
                    flat_sig_items.append((req, ch))
            elif req.type is JsChallengeType.N:
                for ch in req.input.challenges or []:
                    flat_n_items.append((req, ch))

        return flat_sig_items, flat_n_items

    def _prepare_results_map(self, requests: list[JsChallengeRequest]) -> dict[int, dict]:
        results_map: dict[int, dict] = {}
        for req in requests:
            results_map[id(req)] = {'request': req, 'n': {}, 'sig': {}, 'error': None}
        return results_map

    def _yield_responses_from_map(self, results_map: dict[int, dict]) -> typing.Generator[JsChallengeProviderResponse, None, None]:
        for entry in results_map.values():
            req = entry['request']
            if req.type is JsChallengeType.N:
                if entry['n']:
                    yield JsChallengeProviderResponse(request=req, response=JsChallengeResponse(JsChallengeType.N, NChallengeOutput(results=entry['n'])))
            elif req.type is JsChallengeType.SIG:
                if entry['sig']:
                    yield JsChallengeProviderResponse(request=req, response=JsChallengeResponse(JsChallengeType.SIG, SigChallengeOutput(results=entry['sig'])))

    def _real_bulk_solve(self, requests: list[JsChallengeRequest]) -> typing.Generator[JsChallengeProviderResponse, None, None]:
        # Group requests by player_url
        grouped: dict[str, list[JsChallengeRequest]] = collections.defaultdict(list)
        # player_url 其实是 base.js 的 url
        for request in requests:
            grouped[request.input.player_url].append(request)

        # grouped: dict[str, list[JsChallengeRequest]] = {
        #     'https://www.youtube.com/watch?v=dQw4w9WgXcQ': [
        #         JsChallengeRequest(type=JsChallengeType.SIG, input=SigChallengeInput(player_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ', challenges=['sig1', 'sig2', 'sig3'])),
        #         JsChallengeRequest(type=JsChallengeType.N, input=NChallengeInput(player_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ', challenges=['n1', 'n2', 'n3'])),
        #     ]
        # }

        for player_url, grouped_requests in grouped.items():
            # remote cipher server only supports one of each type of challenge at a time (sig + n)
            # flatten the challenge requests so we send sig+n in one go using minimal requests
            # flat_sig_items: list[tuple[JsChallengeRequest, str]] = [ (request, sig1) , (request, sig2) , (request, sig3) , ...]
            # flat_n_items: list[tuple[JsChallengeRequest, str]] = [ (request, n1) , (request, n2) , (request, n3) , ...]
            flat_sig_items, flat_n_items = self._flatten_challenges(grouped_requests)

            player_code = self._get_player(grouped_requests[0].video_id, player_url)
            results_map = self._prepare_results_map(grouped_requests)

            sig_iterable = flat_sig_items or [(None, None)]
            n_iterable = flat_n_items or [(None, None)]

            for (sig_req, sig_val), (n_req, n_val) in itertools.zip_longest(sig_iterable, n_iterable, fillvalue=(None, None)):
                if sig_req is None and n_req is None:
                    continue
                
                
                # Execute javascript by native swift call.
                if not any([sig_val, n_val]):
                    print("Warning: No challenges provided (sig_val and n_val are both empty)")
                    continue
                if not player_code:
                    print("Warning: player_code is required")
                    continue
                    
                request_params = []
                if sig_val and len(sig_val.strip()) > 0:
                    request_params.append({
                        'type': 'sig',
                        'challenges': [sig_val.strip()]
                    })
                    
                if n_val and len(n_val.strip()) > 0:
                    request_params.append({
                        'type': 'n',
                        'challenges': [n_val.strip()]
                    })
                params = {
                    'type': 'player',
                    'player': player_code,
                    'requests': request_params
                }
                current_dir = os.path.dirname(__file__)
                file_path = os.path.join(current_dir, 'yt.solver.standalone.min.js')
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        file_content = file.read()
                        params_json = json.dumps(params, ensure_ascii=False)
                        js_code = f'{file_content}\nytHook.solver({params_json})'
                        result = __main__.execute_javascript(js_code)
                        result_object = json.loads(result)
                        for response in result_object.get('responses'):
                            data = response.get('data', {})
                            if sig_req is not None and sig_val is not None:
                                sig = data.get(sig_val)
                                if sig is not None:
                                    results_map[id(sig_req)]['sig'][sig_val] = sig
                            if n_req is not None and n_val is not None:
                                n = data.get(n_val)
                                if n is not None:
                                    results_map[id(n_req)]['n'][n_val] = n
                except FileNotFoundError:
                    print(f'File yt.solver.standalone.min.js is not found at path: {file_path}.')
                except Exception as e:
                    print(f'Unexpected error: {e}')

            yield from self._yield_responses_from_map(results_map)
