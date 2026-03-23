# AE3GIS Student Guide

**Audience:** Students joining a lab with a join code. No technical background assumed.

---

## 1. Joining Your Lab

Your instructor will give you a **join code** — a short string of letters, numbers, and dashes. You'll use it to access your personal lab.

1. Open a web browser and go to the address your instructor provided (e.g., `http://lab.example.com:3000`)
2. The login screen appears
3. Click the **Student** tab
4. Type your join code into the box
5. Click **Log In**

If you see an error, double-check that you typed the code exactly as given. Join codes are case-sensitive.

---

## 2. Finding Your Way Around

Your lab is organized into three levels. Think of it like zooming in on a map.

### Geographic View — the big picture

When you first log in, you see the **Geographic View**. Each bubble on the screen is a site — a building or network location in your lab.

- **Click a site** to go inside it

### Subnet View — inside a site

After clicking a site, you see the **Subnet View**. Each cloud shape is a subnet — a group of devices on the same network segment.

- **Click a subnet cloud** to see the individual devices inside it
- **Use the breadcrumb** at the top (e.g., `Home > Corporate Office`) to go back to the previous level

### LAN View — individual devices

After clicking a subnet cloud, you see the **LAN View** — the actual devices (computers, routers, servers, etc.).

Each device has a small colored dot:
- **Green dot** — the device is running and ready
- **Red dot** — the device is stopped or not yet deployed

Use the breadcrumb at the top to navigate back up.

---

## 3. Opening a Terminal

A terminal lets you type commands directly on a device — like opening a command prompt on that machine.

To open a terminal:

1. Navigate to the LAN View (click a site, then click a subnet cloud)
2. Find the device you want to connect to — it must have a **green dot**
3. Click on the device node
4. A terminal tab opens at the bottom of the screen

You're now connected to that device. Type your commands and press Enter.

---

## 4. Using the Terminal

**Multiple terminals:** You can open terminals to more than one device. Each device gets its own tab at the bottom of the screen. Click a tab to switch between devices.

**Minimize:** Click the minimize button (−) in the terminal panel header to hide the terminals without closing them. Click it again to bring them back.

**Refresh warning:** If you refresh or reload the page, all open terminals will close. You'll need to click the devices again to re-open them.

---

## 5. The Purdue Model View

If your instructor has enabled it, you may see a **Purdue** button in the top-right area of the screen.

Clicking it opens the **Purdue Model View**, which shows how the devices in your lab are organized into security zones and levels. This is a read-only diagram — you can't make changes here.

Your instructor may ask you to refer to this view during certain exercises.

---

## 6. What You Can and Cannot Do

As a student, your access is intentionally limited:

**You can:**
- View the topology (all three levels)
- See device status (green/red dots)
- Open terminals to running devices
- View the Purdue Model diagram
- View scenarios (read-only)

**You cannot:**
- Create, edit, or delete topology elements
- Save or export the topology
- Deploy or destroy the lab
- Access other students' labs
- Access the classroom management panel

---

## 7. Troubleshooting

**"Invalid join code" error on login**
- Check that you copied the code exactly — no extra spaces, correct capitalization
- Ask your instructor to confirm the join code is correct

**Devices show red dots**
- The lab may not be deployed yet. Ask your instructor to deploy it.
- If some devices are red and others are green, those specific containers may have crashed — let your instructor know.

**Terminal stuck on "Connecting…"**
- The device must be green (running) before you can connect
- Wait a few seconds for the container to finish starting, then try again
- If it stays stuck, try clicking a different device first, then come back

**Terminal shows garbage characters or strange output**
- This can happen if the terminal size doesn't match. Try resizing the terminal panel by dragging its top edge.

**Blank page or nothing loads**
- Reload the page and log in again with your join code
- If the problem continues, let your instructor know
