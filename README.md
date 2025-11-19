# Omni Vision Tuner 

**This plugin provides Omniverse users with a set of lighting and material management tools, mainly used for lighting management, sun path simulation, and material management in scenes, especially suitable for users who need to finely control lighting and optimize scene resources.**

Architectural Visualization: Accurate Sunlight Analysis and Lighting Adjustment
Product rendering: material optimization and lighting layout
Scenario optimization: Clean up unused resources and improve performance
Lighting Design: Complex Multi level Lighting System Management

```LightManager
        
        # Directory Structure
        /World/lights/                  # Root Path
            ├── LivingRoom/             # Room (Secondary Catalog)
            │   ├── MainLights/         # Lighting Group (Level 3 Catalog)  
            │   │   ├── SpotLight1      # Specific Lighting
            │   │   └── SpotLight2
            │   └── AccentLights/
            └── Bedroom/
                └── BedsideLights/
        
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

### Requirements
- Requires Omniverse Kit >= 108

### Test in Omniverse

1. `Window` > `Extensions`
2. ☰ > Settings
3. ✚ Add `_install\windows-x86_64\release` folder to the Extension Search Paths
4. The user extension should appear on the left
5. `Autoload` needs to be checked for the FileFormat plugin to be correctly loaded at USD Runtime.

```
        git clone https://github.com/9Din/omni_Lighting_Control.git
```

