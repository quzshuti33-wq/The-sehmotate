local http = require("socket.http")
local ltn12 = require("ltn12")
local json = require("dkjson")

-- 🔧 إعدادات
local TOKEN = "7525686307:AAHeakAco2BR1nX37uWNkjxDYBFvnFQEqP4"
local OWNER_USERNAME = "CH_XW" -- بدون @
local OWNER_BUTTON_TEXT = "المالك"
local API_URL = "https://api.telegram.org/bot" .. TOKEN .. "/"
local POLL_INTERVAL = 1

-- 📩 دالة لإرسال طلبات API
local function api_request(method, params)
  local url = API_URL .. method
  local body = json.encode(params or {})
  local resp = {}
  http.request{
    url = url,
    method = "POST",
    headers = {
      ["Content-Type"] = "application/json",
      ["Content-Length"] = tostring(#body)
    },
    source = ltn12.source.string(body),
    sink = ltn12.sink.table(resp)
  }
  local raw = table.concat(resp)
  local data = json.decode(raw)
  return data
end

-- 🕒 تنسيق الوقت والتاريخ
local function format_datetime(ts)
  local t = os.date("*t", ts)
  return string.format("%04d-%02d-%02d", t.year, t.month, t.day),
         string.format("%02d:%02d:%02d", t.hour, t.min, t.sec)
end

-- 📸 نحصل على صورة القروب
local function get_chat_photo(chat_id)
  local res = api_request("getChat", {chat_id = chat_id})
  if res and res.result and res.result.photo then
    return res.result.photo.big_file_id
  end
  return nil
end

-- 🔗 نحصل على رابط القروب
local function get_group_link(chat)
  if chat.username then return "https://t.me/"..chat.username end
  local res = api_request("exportChatInviteLink", {chat_id = chat.id})
  if res and res.result then return res.result end
  return nil
end

-- 🎉 إرسال رسالة الترحيب
local function send_welcome(chat, member, join_time)
  local name = member.first_name or "عضو جديد"
  local user = member.username and ("@" .. member.username) or "لا يوجد"
  local date, time = format_datetime(join_time)
  local group_link = get_group_link(chat)
  local photo = get_chat_photo(chat.id)

  local text = table.concat({
    "✦ أهلاً عزيزي، نورت قروبنا " .. (chat.title or ""),
    "",
    "• اسمك: " .. name,
    "• يوزرك: " .. user,
    "• تاريخ دخولك: " .. date,
    "• وقت دخولك: " .. time
  }, "\n")

  local buttons = {
    inline_keyboard = {{
      { text = chat.title or "رابط القروب", url = group_link or "https://t.me" },
      { text = OWNER_BUTTON_TEXT, url = "https://t.me/" .. OWNER_USERNAME }
    }}
  }

  local params = {
    chat_id = chat.id,
    caption = text,
    parse_mode = "HTML",
    reply_markup = buttons
  }

  if photo then
    params.photo = photo
    api_request("sendPhoto", params)
  else
    params.text = params.caption
    params.caption = nil
    api_request("sendMessage", params)
  end
end

-- 🔁 حلقة التشغيل
local offset = 0
while true do
  local updates = api_request("getUpdates", {offset = offset, timeout = 20, allowed_updates={"message"}})
  if updates and updates.result then
    for _, upd in ipairs(updates.result) do
      offset = upd.update_id + 1
      local msg = upd.message
      if msg and msg.new_chat_members then
        for _, m in ipairs(msg.new_chat_members) do
          send_welcome(msg.chat, m, msg.date or os.time())
        end
      end
    end
  end
  os.execute("sleep " .. POLL_INTERVAL)
end
