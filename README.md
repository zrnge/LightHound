# 🛡️ LightHound
LightHound is a lightweight, standalone Active Directory (AD) attack path visualizer. It provides a simple, interactive GUI to analyze SharpHound JSON exports without the need for Neo4j, Java, or complex database configurations.

✨ Features

- Interactive Graph Engine: Drag nodes to reorganize, scroll to zoom, and right-click to pan.

- DACL Awareness: Automatically parses permissions like GenericAll, WriteDacl, Owns, and more.

- Shortest Path Analysis: One-click pathfinding from any user to the "Domain Admins" group.

- Deep Detail Panel: Click any node to see the full raw JSON data collected by SharpHound.

- Zero Dependencies: Built entirely with standard Python libraries (tkinter, json, zipfile).

## Color Coded:

  - 🔵 Users

  - 🟢 Groups

  - 🟠 Computers

  - 🟡 High Value (Tier 0)
