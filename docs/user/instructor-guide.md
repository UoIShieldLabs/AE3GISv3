# AE3GIS Instructor Guide

**Audience:** Instructors building and running network labs.

---

## 1. Logging In

1. Navigate to `http://<server-address>:3000`
2. The login dialog opens automatically
3. Select the **Instructor** tab
4. Enter your instructor token (provided by your system administrator)
5. Click **Log In**

If you don't know your token, contact whoever set up the server. The token is configured via the `AE3GIS_INSTRUCTOR_TOKEN` environment variable.

---

## 2. The Interface at a Glance

The interface has three main regions:

**Header bar (top):**
- *Left:* AE3GIS title + save controls (New, Save, Load, Export)
- *Center:* Topology name (large), deployment status pill, site and container counts
- *Right:* Action buttons — Deploy, Destroy, Classroom, Scenarios, Logout

**Canvas (center):** The main work area. Shows a different view depending on which level you've drilled into.

**Breadcrumb (top of canvas):** Shows your current position (e.g., `Home > Site A > Subnet 1`) and lets you navigate back up.

**Terminal panel (bottom, when open):** Terminal tabs for connected containers.

---

## 3. Three-Level Navigation

AE3GIS organizes network topologies at three levels:

| Level | What you see | How to enter |
|-------|-------------|--------------|
| **Geographic** | Sites as nodes on a canvas | App start |
| **Subnet** | Subnet clouds + routers within one site | Click a site node |
| **LAN** | Individual devices within one subnet | Click a subnet cloud |

Use the breadcrumb at the top of the canvas to navigate back up.

---

## 4. Building a Topology

### Creating sites

A *site* represents a physical or logical location (e.g., Corporate Office, OT Floor).

1. Right-click the canvas → **Add Site**
2. Enter a name and optional location label
3. Drag the site node to position it on the canvas
4. To connect two sites (inter-site link), drag from the edge of one site node to another

### Adding subnets

A *subnet* represents a network segment within a site.

1. Click a site to enter the Subnet view
2. Right-click the canvas → **Add Subnet**
3. Enter a name and CIDR (e.g., `10.0.1.0/24`)
4. Optionally set a gateway IP — if left blank, the first router or firewall in the subnet is used as the gateway automatically at deploy time

> **Tip:** Adding a subnet automatically creates a router and a switch, pre-wired together. You don't need to add them manually.

### Adding devices

1. In the LAN view (click a subnet cloud), right-click the canvas → **Add Device**
2. Choose a device type and enter a name and IP address

Device types:

| Type | Plain-language description |
|------|---------------------------|
| `workstation` | End-user PC or laptop |
| `web-server` | HTTP server |
| `file-server` | File sharing server |
| `plc` | Programmable Logic Controller (industrial control) |
| `firewall` | Packet-filtering firewall (also routes) |
| `router` | Layer-3 router |
| `switch` | Layer-2 switch (bridge) |

3. To connect two devices, drag from one node's edge handle to another
4. For cross-subnet connections: in the Subnet view, drag from one subnet cloud to another — gateway routers are created automatically

### Layout options

In the Subnet view and LAN view, use the layout toggle (Tree / Circle / Grid) to rearrange nodes:

- **Tree** — Hierarchical layout; best for hub-and-spoke topologies
- **Circle** — Ring layout; good for visualizing peer relationships
- **Grid** — Uniform grid; good for large flat topologies

### Saving

Click **Save** in the header bar. The pencil (dirty) indicator in the status area clears when the topology is saved.

> **Tip:** You don't need to save before deploying — the Deploy button auto-saves if there are unsaved changes.

---

## 5. Deploying a Topology

1. Click **Deploy** in the header bar
2. The status pill transitions: `idle` → `deploying` → `deployed`
3. Once deployed, container nodes show a colored status dot:
   - **Green** — container is running
   - **Red** — container is stopped or unreachable

To stop the simulation, click **Destroy**. All containers are stopped and removed. The topology definition is preserved — you can deploy again.

---

## 6. Using Terminals

1. Make sure the topology is deployed and the target container's dot is **green**
2. Click the container node in the LAN view
3. A terminal tab opens at the bottom of the screen
4. Type commands directly in the terminal

You can open terminals to multiple containers simultaneously — each gets its own tab. Click a tab to switch between them. Click the minimize button to hide the terminal panel without closing sessions.

> **Warning:** Terminal sessions are not preserved across page refreshes. If you reload the page, open terminals will need to be re-opened.

---

## 7. Firewall Rules

For `router` and `firewall` containers, you can manage packet-filtering rules from the UI:

1. Right-click the container node → **Firewall Rules**
2. The rule editor dialog opens, showing the current rule set
3. Click **Add Rule** to add a new rule (source IP, destination IP, protocol, port, allow/deny)
4. Click the trash icon to delete a rule
5. Click **Apply** to push the rules to the container

> **Note:** Firewall rules are applied live but are not persisted in the topology definition. They will be lost when the topology is destroyed and redeployed.

---

## 8. The Purdue Model View

Click the **Purdue** button in the header bar to open the Purdue Model overlay.

This view automatically classifies your topology's containers into Purdue Model zones and levels:

| Zone | Classification rule |
|------|-------------------|
| OT | Contains PLCs |
| DMZ | Contains servers only (no workstations) |
| IT | Everything else |

Levels within zones are assigned automatically based on device type. The view is read-only — use it to verify your topology reflects the intended Purdue Model structure.

---

## 9. Classroom Management

### Creating a session

1. Click **Classroom** in the header bar
2. Click **New Session**
3. Enter a session name and select a template topology (the topology that will be cloned for each student)
4. Click **Create**

### Instantiating student slots

1. Open the session
2. Click **Instantiate Slots**
3. Enter the number of students and an optional label prefix (e.g., `Student` → Student 1, Student 2, …)
4. Click **Instantiate**

Each slot gets:
- A deep copy of the template topology (fully independent)
- A unique join code (UUID)

### Distributing join codes

The slot list shows each student's label and join code. Share the join code with each student — they'll use it to log in to their own topology instance.

Students navigate to the same URL and select the **Student** login tab.

### Deploying student topologies

- **Individual deploy:** Click the Deploy button next to a single slot
- **Batch Deploy:** Click **Batch Deploy** to deploy all slots simultaneously

> **Note:** Batch deploy runs a maximum of **3 deployments concurrently** to avoid overloading the host. All slots are queued and processed in batches of 3.

### Monitoring student status

The slot list shows the deployment status for each student's topology. Refresh to see updates.

---

## 10. Attack Scenarios

### Creating a scenario

1. Click **Scenarios** in the header bar
2. Click **New Scenario**, enter a name and optional description
3. Click **Add Phase** to add attack phases in sequence
4. For each phase, click **Add Execution** to define:
   - **Target container** — which container the script runs on
   - **Script** — select from available scripts (auto-populated from `backend/scripts/`)
   - **Args** — optional command-line arguments

### Executing a phase

1. Open the scenario panel
2. Click **Execute** next to a phase
3. Results appear inline: return code, stdout, and stderr for each execution

### Batch execution across classroom slots

When a classroom session is active, the scenario panel shows a **Batch Execute** option. This runs the selected phase against the corresponding container in every student slot simultaneously.

### Loading the Stuxnet preset

1. Click **Load** → **From Preset**
2. Select **Stuxnet ICS Attack**
3. Click **Load**

This creates a pre-built topology with Corporate, DMZ, and OT/SCADA sites, plus a complete Stuxnet kill-chain scenario with phases for initial infection, lateral movement, and PLC manipulation.

---

## 11. Importing and Exporting

### Export to JSON

Click **Export** in the header bar. The topology is downloaded as a `.json` file containing all sites, subnets, containers, connections, and scenarios.

### Import from JSON

Click **Load** → **From File** and select a previously exported `.json` file.

### Import from ContainerLab YAML

Click **Load** → **Import .clab.yml** and select a ContainerLab topology file. The importer groups containers into subnets by CIDR and into sites by the `group` field.

> **Note:** The importer creates a best-effort representation. Complex ContainerLab topologies may require manual adjustment after import.
