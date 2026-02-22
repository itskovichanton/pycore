from dataclasses import dataclass

from src.mybootstrap_core_itskovichanton.ssh import SSHConfig, DownloadFileArgs

from src.mybootstrap_core_itskovichanton.utils import with_empty_method
from src.mybootstrap_mvc_itskovichanton.exceptions import CoreException

from src.mybootstrap_core_itskovichanton.curl.builder import CURL_CMD_DEFAULT, CurlBuilder
from src.mybootstrap_core_itskovichanton.shell import ShellService
from src.mybootstrap_ioc_itskovichanton.ioc import bean


def _build_curl_cmd(curl_command: str):
    return f"""
#!/bin/bash
output=$(mktemp)
error_output=$(mktemp)
headers=$(mktemp)

{curl_command} >"$output" 2>"$error_output"

response_headers=$(cat "$headers")
response_body=$(cat "$output")

rm "$headers" "$output" "$error_output"

echo "---RESPONSE-HEADERS---"
echo "$response_headers"
echo "---RESPONSE-BODY---"
echo "$response_body"
echo "---ERROR---"
echo "$(cat "$error_output")"
"""


@with_empty_method
@dataclass
class Response:
    headers: dict
    body: str
    code: str
    downloaded_file: DownloadFileArgs = None


def _parse_response(output: str) -> Response:
    if '---RESPONSE-HEADERS---' in output and '---RESPONSE-BODY---' in output and "---ERROR---" in output:
        headers_part = output.split('---RESPONSE-HEADERS---')[1].split('---RESPONSE-BODY---')[0].strip()
        body_part = output.split('---RESPONSE-BODY---')[1].split('---ERROR---')[0].strip()
        error = output.split('---ERROR---')[1].strip()
        if error and ('cat: /tmp/' not in error):
            raise CoreException(message=error)

        lines = headers_part.split('\n')
        response_code = lines[0]  # Первая строка - код ответа
        headers = {}

        for line in lines[1:]:
            # Пытаемся разделить строку по первому ': ' для получения пары ключ-значение
            parts = line.split(': ', 1)
            if len(parts) != 2:
                continue  # Если не удалось разделить, переходим к следующей строке

            key, value = parts
            if key in headers:
                # Если ключ уже существует, то добавляем новое значение в список
                if isinstance(headers[key], list):
                    headers[key].append(value)
                else:
                    headers[key] = [headers[key], value]
            else:
                headers[key] = value

        return Response(code=response_code, headers=headers, body=body_part)

    raise CoreException(message=f"cannot parse response, curl output={output}")


@bean
class Curl:
    shell: ShellService

    def execute(self, curl_builder: CurlBuilder, cwd=None, ssh_config: SSHConfig = None) -> Response:
        curl_cmd = curl_builder.verbose().store_headers_file('"$headers"').build()
        if ssh_config and curl_builder.get_output():
            ssh_config.download_file_args = DownloadFileArgs(remote_path=curl_builder.get_output())
        curl_output = self.shell.execute_bash(_build_curl_cmd(curl_cmd), cwd=cwd, ssh_config=ssh_config)
        r = _parse_response(curl_output)
        if r.empty():
            raise CoreException(message="Пустой результат curl. Возможно нужно выполнять с sudo")
        if ssh_config:
            r.downloaded_file = ssh_config.download_file_args
        return r
