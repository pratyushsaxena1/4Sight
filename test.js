fetch("https://lms.fcps.edu/usage/collect", {
    "headers": {
      "accept": "*/*",
      "accept-language": "en-US,en;q=0.9",
      "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VySWQiOiIxMDgyMjMyNjgiLCJzY2hvb2xJZCI6IjIxODM0MTAwNTUiLCJuYW1lc3BhY2UiOiJzY2hvb2xvZ3kiLCJpYXQiOjE3Mzc3MzA5NjMsImV4cCI6MTczNzc1MjU2MywiaXNzIjoiYXBwLnNjaG9vbG9neS5jb20ifQ.KJaTZBqs2XNFaRkt-CwEIAG42ErsHNzazIXdKOSNIp0",
      "content-type": "application/json",
      "priority": "u=1, i",
      "sec-ch-ua": "\"Google Chrome\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
      "sec-ch-ua-mobile": "?0",
      "sec-ch-ua-platform": "\"macOS\"",
      "sec-fetch-dest": "empty",
      "sec-fetch-mode": "same-origin",
      "sec-fetch-site": "same-origin"
    },
    "referrer": "https://lms.fcps.edu/course/7396187228/materials/gp/7671087766",
    "referrerPolicy": "strict-origin-when-cross-origin",
    "body": "{\"user_id\":\"108223268\",\"school_id\":\"2183410055\",\"tz\":\"America/New_York\",\"client_type\":\"WEB\",\"client_version\":\"Chrome Dev 131.0.0.0\",\"env\":\"app.schoology.com\",\"metrics\":[{\"material_id\":\"7671087766\",\"material_type\":\"FILE\",\"course_section_id\":\"7396187228\",\"duration\":32903,\"ref_time\":1737730996,\"trace_id\":\"d6c39fab-27ed-4669-be40-b799c6bcd301\",\"session_id\":\"b7e441b7-777e-44da-a728-a014a5b770f5\"}]}",
    "method": "POST",
    "mode": "cors",
    "credentials": "include"
  });