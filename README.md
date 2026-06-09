<img height=200px src="docs/assets/graphical-banner.png" alt="Soteria banner">

<p>
    <img src="https://raw.githubusercontent.com/RMIT-Competition-Rocketry/.github/refs/heads/main/assets/hive_badge.svg" height="20rem" alt="Hive badge">
    <img alt="Static Badge" src="https://img.shields.io/badge/status-Deployed_for_IREC_2026-green">
    <img src="https://github.com/RMIT-Competition-Rocketry/GCS/actions/workflows/build_and_test_cpp.yml/badge.svg" height="20rem" alt="Build and test CPP badge">
    <img src="https://img.shields.io/github/v/release/RMIT-Competition-Rocketry/GCS?label=version" height="20rem">
</p>

![banner](docs/assets/banner.png)

Repository for RMIT HIVE's rocketry GCS (**Ground Control Station**).

**Named after Soteria, the Greek goddess of safety and deliverance from harm.**

<p align="center">
  <img src="docs/assets/serp2launchSetup.jpg" height="200px" alt="Serpentine launch setup"/>
  <img src="docs/assets/serp2launch.jpg" height="200px" alt="Serpentine launch">
</p>
<p align="center">
  <img src="docs/assets/irec2025stand.jpeg" height="250px" alt="Stand at IREC 2025"/>
</p>

© 2026 RMIT Competition Rocketry - Licensed under the MIT License

## Documentation

### Contributing

Before working with this repository, please read [Contributing](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests. You can find the [AI policy](CONTRIBUTING.md#ai-policy) here.

### Table of Contents

- [Setup](docs/setup.md)
- [Usage](docs/usage.md)
- [Pendant Emulator Quick Reference](docs/pendant_emulator.md)
- [System Design & features](docs/system_design.md)
- [Development](docs/development.md)
- [Tutorials](docs/tutorials.md)
- [Frontend](docs/frontend.md)
- [Glossary](docs/glossary.md)

<!-- ### Notes

- [Brainstorming](notes/brainstorming.md)
- [Data](notes/data.md) -->

## Description

The GCS, known as SOTERIA, is Hive's computer control system for GSE control, avionics communication, and data visualisation. The core of the GCS is a single computer running SRAD software with SRAD LoRa radio hardware peripherals. All OSI layers in our networking stack above the physical protocol are SRAD for use with our Australis (avionics) ecosystem. The software converts raw serial input from physical radio interfaces into human-readable output for efficient system monitoring by the GCS operator and visualisations for observers. We use a WebSocket and a protocol buffer based IPC API to communicate with our GCS services. Our web frontend is fully SRAD aside from industry-standard libraries. The GCS operator can see if any system is performing sub-optimally via alert and warning readouts, so they can make an informed GO/NO-GO call quickly. Spectators and other team members have access to several different views detailing all telemetry from both the GSE and avionics systems

## Credit

Ground Control Software Team

<table>
    <tr>
        <th>Name</th>
        <th>Role</th>
        <th>Year</th>
    </tr>
    <tr>
        <td rowspan=2><a href="https://www.linkedin.com/in/freddy-mcloughlan/">Freddy Mcloughlan</a> (<code>mcloughlan</code>)</td>
        <td>IREC 2026 lead</td>
        <td>2026</td>
    </tr>
    <tr>
        <td>GCS software lead & backend software engineer</td>
        <td>2025</td>
    </tr>
    <tr>
        <td rowspan=2><a href="https://www.linkedin.com/in/amber-taylor-20bb63264/">Amber Taylor</a> (<code>s4105951</code>)</td>
        <td>GCS IREC 2026 lead & senior software engineer</td>
        <td>2026</td>
    </tr>
    <tr>
        <td>GCS frontend lead & software developer</td>
        <td>2025</td>
    </tr>
    <tr>
        <td rowspan=2><a href="https://www.linkedin.com/in/trist4nl3/">Tristan Le</a> (<code>trist4nl3</code>)</td>
        <td>GSE (Ground Service Equipment) & electronics lead</td>
        <td>2026</td>
    </tr>
    <tr>
    <td>GCS simulation integration</td>
        <td>2025</td>
    </tr>
    <tr>
        <td><a href="https://www.linkedin.com/in/xavier-egan-a5b3b027a/">Xavier Egan</a> (<code>XavierEgan</code>)</td>
        <td>GCS AURC 2026 lead & software developer</td>
        <td>2026</td>
    </tr>
    <tr>
        <td><a href="https://www.linkedin.com/in/twhlynch/">Tom Lynch</a> (<code>twhlynch</code>)</td>
        <td>GCS software developer</td>
        <td>2026</td>
    </tr>
    <tr>
        <td>Joseph Di Giulio (<code>WhiteNoisex</code>)</td>
        <td>GCS software engineer & refactoring</td>
        <td>2026</td>
    </tr>
    <tr>
        <td>Zachary Everett (<code>zachever</code>)</td>
        <td>GCS software</td>
        <td>2026</td>
    </tr>
    <tr>
        <td>Kelly Wan Wing Kai (<code>kelly2504</code>)</td>
        <td>GCS web designer</td>
        <td>2026</td>
    </tr>
    <tr>
        <td><a href="https://www.linkedin.com/in/marven-wijesiriwardena-252254389/">
        Marven Wijesiriwardena</a>
        (<code>MarvenW</code>)
        </td>
        <td>GCS UI/UX dev</td>
        <td>2026</td>
    </tr>
    <tr>
    <td><a href="https://www.linkedin.com/in/michael-iurovetski-5742632a1/">
        Michael Iurovetski</a>
        (<code>Iurovet</code>)
        </td>
        <td>GCS UX and sound effects designer</td>
        <td>2026</td>
    </tr>
    <tr>
        <td>Mohammad Ullah
        (<code>mov360</code>)
        </td>
        <td>GCS QA & Software Engineer (Frontend)</td>
        <td>2026</td>
    </tr>
    <tr>
        <td><a href="https://www.linkedin.com/in/caspar-oneill/">Caspar O'Neill</a> (<code>s3899921</code>)</td>
        <td>GCS frontend API engineer</td>
        <td>2025</td>
    </tr>
    <tr>
        <td><a href="https://www.linkedin.com/in/anuk-jayasundara-ab440b1aa/">Anuk Jayasundara</a> (<code>SaviruA</code>)</td>
        <td>GCS 6DOF rocket visualisation</td>
        <td>2025</td>
    </tr>
    <tr>
        <td>Jonathan Do (<code>J88error</code>)</td>
        <td>GCS frontend UI/UX design</td>
        <td>2025</td>
    </tr>
    <tr>
        <td>Nathan La (<code>s4003562</code>)</td>
        <td>GCS data visualisation</td>
        <td>2025</td>
    </tr>
</table>

Special thanks

- [The DiSTI Corporation](https://www.disti.com/)
    - For access to GL Studio to accompany the GCS
- Aleksei Eaves
    - For 2026 flight computer firmware development
- [Jonathan Chandler](https://www.linkedin.com/in/jonathan-chandler-03474b1ba/)
    - 2025 GCS Lead. The all-knowing being of ground control and operations
- [Matthew Ricci](https://www.linkedin.com/in/matthewricci-embedded/)
    - Flight computer [avionics firmware](https://github.com/RMIT-Competition-Rocketry/Australis-Avionics-firmware) lead.

And to all those at RMIT Hive!

## Software Development Components

This project was built using the following tools, languages and systems.

- Radio commuincation:
  - [LoRa](https://en.wikipedia.org/wiki/LoRa) with both COTS and SRAD hardware
- Multithreaded data ingestion server
  - Written in C++
  - Built with [ZeroMQ](https://zeromq.org/) for IPC communication
  - IPC Data serialisation with [Google's Protocol Buffers](https://protobuf.dev/)
- Multithreaded CLI based process manager
  - Written in Python
  - Includes a device emulator for internal system tests that attaches from the hardware layer to create a fake unix device file at `/dev/`

**Cool fact**: Our GCS runs at less than 1% CPU utilization on a Raspberry Pi 5 during regular use.

## Screenshots

### 2026

| Rocket selection screen | Main view | Pre-flight view |
| --- | --- | --- |
| <img width="1920" height="1080" alt="Screenshot 2026-06-09 at 11-35-57 ROCKET SELECTOR - RMIT High Velocity" src="https://github.com/user-attachments/assets/ac3f7848-796f-4d68-b25f-364a808c3dd2" /> | <img width="1920" height="1080" alt="Screenshot 2026-06-09 at 11-36-51 Horizon - RMIT High Velocity" src="https://github.com/user-attachments/assets/d5e2f2ed-e746-413f-aa18-db44d27f5195" /> | <img width="1920" height="1080" alt="Screenshot 2026-06-09 at 11-37-11 Horizon - RMIT High Velocity" src="https://github.com/user-attachments/assets/b909149e-3015-4c2c-b2e4-de97f4a01b26" />

### 2025

| Web interface (main view) | Custom GSE HMI page | CLI |
| --- | --- | --- |
| ![GUI interface](docs/assets/frontend-example.png) | ![HMI page](docs/assets/hmi-example.png) | ![CLI interface](docs/assets/cli.png) |

## Conference Appearances

[PyCon AU 2026](https://2026.pycon.org.au/schedule/9KBBEQ/), August 2026

## License and Attribution

This project is licensed under the MIT License.

If you use or modify this software, you **must retain** the original copyright
notice and license in all copies or substantial portions of the Software.

Attribution must be clearly displayed in any redistributed or derivative works.

Please credit: **RMIT Competition Rocketry** and the **Hive GCS Software Team**.

See the [LICENSE](LICENSE) file for full terms.
