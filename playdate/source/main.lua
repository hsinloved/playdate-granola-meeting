-- Granola Remote for Playdate
-- Press A to start a Granola note on your Mac, B to stop (if configured), ↑ to ping.
-- Talks to mac-helper/granola_helper.py over your local Wi-Fi.

import "CoreLibs/graphics"
import "config"

local pd <const> = playdate
local gfx <const> = pd.graphics
local net <const> = pd.network

-- state: "idle" | "sending" | "ok" | "error"
local state = "idle"
local message = "Press A to start notes"
local lastAction = nil
local conn = nil
local body = ""

local function setStatus(newState, msg)
    state = newState
    message = msg
end

local function closeConn()
    if conn then
        conn:close()
        conn = nil
    end
end

local function sendRequest(action)
    if state == "sending" then return end
    closeConn()
    body = ""
    lastAction = action

    -- net.http.new(server, port, useHttps, reasonShownToUser)
    -- First run: Playdate OS asks the user to allow access to this server.
    local c, err = net.http.new(CONFIG.host, CONFIG.port, false, "Send start/stop commands to Granola on your Mac")
    if not c then
        setStatus("error", "No network access:\n" .. tostring(err or "allow it in the prompt / Settings"))
        return
    end
    conn = c
    conn:setConnectTimeout(CONFIG.timeoutSeconds)

    conn:setRequestCompleteCallback(function()
        local status = conn:getResponseStatus()
        local n = conn:getBytesAvailable()
        if n and n > 0 then body = body .. (conn:read(n) or "") end
        if status == 200 then
            if action == "start" then setStatus("ok", "Granola is taking notes")
            elseif action == "stop" then setStatus("ok", "Stopped")
            else setStatus("ok", "Mac helper is reachable") end
        else
            setStatus("error", "Helper replied " .. tostring(status) .. "\n" .. body)
        end
        closeConn()
    end)

    conn:setConnectionClosedCallback(function()
        if state == "sending" then
            local e = conn and conn:getError() or nil
            setStatus("error", "Connection closed\n" .. tostring(e or "is the helper running?"))
        end
    end)

    local path = "/" .. action .. "?token=" .. CONFIG.token
    local ok, reqErr = conn:get(path)
    if not ok then
        setStatus("error", "Request failed:\n" .. tostring(reqErr))
        closeConn()
        return
    end
    setStatus("sending", action == "ping" and "Pinging Mac..." or "Talking to Granola...")
end

-- Network calls are only allowed from inside playdate.update(), so button
-- handlers just queue an action and update() performs it.
local pendingAction = nil
local wifiRequested = false

local function ensureWifi()
    if wifiRequested or not net.setEnabled then return end
    wifiRequested = true
    -- Playdate powers Wi-Fi down to save battery; turn it on.
    net.setEnabled(true, function(err)
        if err then setStatus("error", "Wi-Fi error: " .. tostring(err)) end
    end)
end

local function drawCentered(text, y, font)
    if font then gfx.setFont(font) end
    gfx.drawTextAligned(text, 200, y, kTextAlignment.center)
end

function pd.update()
    ensureWifi()
    if pendingAction then
        local a = pendingAction
        pendingAction = nil
        sendRequest(a)
    end

    gfx.clear(gfx.kColorWhite)

    -- Big status disc
    if state == "ok" and lastAction == "start" then
        gfx.fillCircleAtPoint(200, 80, 40)               -- solid = recording
    elseif state == "sending" then
        local r = 30 + math.floor(math.sin(pd.getCurrentTimeMilliseconds() / 150) * 6)
        gfx.drawCircleAtPoint(200, 80, r)
    elseif state == "error" then
        gfx.drawLine(170, 50, 230, 110); gfx.drawLine(230, 50, 170, 110)
    else
        gfx.drawCircleAtPoint(200, 80, 40)
    end

    drawCentered("*GRANOLA REMOTE*", 10)
    gfx.drawTextInRect(message, 20, 135, 360, 60, nil, "...", kTextAlignment.center)
    drawCentered("Ⓐ start   Ⓑ stop   ⬆️ ping", 215)
end

function pd.AButtonDown() pendingAction = "start" end
function pd.BButtonDown() pendingAction = "stop" end
function pd.upButtonDown() pendingAction = "ping" end
