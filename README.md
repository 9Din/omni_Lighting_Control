# Omni Vision Tuner 

> This plugin provides Omniverse users with a set of lighting and material management tools, mainly used for lighting management, sun path simulation, and material management in scenes, especially suitable for users who need to finely control lighting and optimize scene resources.

<br>

 Architectural Visualization: Accurate Sunlight Analysis and Lighting Adjustment
 Product rendering: material optimization and lighting layout
 Scenario optimization: Clean up unused resources and improve performance
 Lighting Design: Complex Multi level Lighting System Management

```
        LightManager   
        # Directory Structure

        /World/
            ├── lights/                         # Root Path
                ├── LivingRoom/                 # Room (Secondary Catalog)
                │   ├── CeilingLights/          # Lighting Group (Level 3 Catalog)  
                │   │   │   ├── SpotLight1      # Specific Lighting
                │   │   │   └── SpotLight2
                │   └── AccentLights/
                │           └── CylinderLight
                └── Bedroom/
                    └── BedsideLights/
                            └── DiskLight
                
```
Core Capabilities
- Precision Color Science
Leveraging industry-standard color temperature curves, it enables seamless transitions from cool moonlight to warm sunset glow, ensuring both authentic color reproduction and pure artistic expression.

- Dynamic Intensity Management
Offers global intensity control, from macro scene lighting to micro object fill lights, empowering you to shape visual hierarchy with depth and drama.

- Centralized Command Hub
Through an intuitive unified panel, it enables coordinated switching, grouping, and state management of multiple light sources within a scene, significantly enhancing iteration efficiency.

- Non-Destructive Real-Time Preview
All adjustments are instantly reflected in Omniverse's real-time viewport, achieving zero latency between creative decisions and final results.

## Quick Start

**Target applications:** NVIDIA Omniverse App

**Supported OS:** Windows and Linux

**Changelog:** [CHANGELOG.md](exts/omni.LightingControl/docs/CHANGELOG.md)

**Table of Contents:**


- [Extension usage](#usage)
  - [Code autocompletion](#usage-autocompletion)
  - [Code introspection](#usage-introspection)
- [Configuring the extension](#config)
- [Implementation details](#implementation)

<br>

![showcase](exts/omni.LightingControl/data/preview.png)

<hr>

<a name="usage"></a>
### Extension usage

#### Requirements
- Requires Omniverse Kit >= 108


### Adding This Extension
To add this extension to your Omniverse app:

1. `Developer` > `Extensions` or `Window` > `Extensions`
2. ☰ > Settings
3. ✚ Add `git:https://github.com/9Din/omni_Lighting_Control/tree/main/exts` folder to the Extension Search Paths
4. The user extension should appear on the left
5. `Autoload` needs to be checked for the FileFormat plugin to be correctly loaded at USD Runtime.
        
Manual installation:

1. Download Zip  ` git clone https://github.com/9Din/omni_Lighting_Control.git `
2. Extract and place into a directory of your choice
3. `Developer` > `Extensions` or `Window` > `Extensions`
4. ☰ > Settings
5. ✚ Add `\omni_Lighting_Control\exts` folder to the Extension Search Paths
6. The user extension should appear on the left
7. `Autoload` needs to be checked for the FileFormat plugin to be correctly loaded at USD Runtime.



