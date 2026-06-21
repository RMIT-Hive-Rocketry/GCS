# Replay System

## About

This replay system allows data to be played on the GCS websocket in "real time". It has the ability to play both pre and post data from previous missions or simulations. It will give a near replica of what it would be like in the field.

## Data Obtainment method

- Simulations
  - From rocketpy as of 12-05-2025
- Missions
  - From Serpentine, only current mission is 04-05-2025

## Usage

To run this code in the cli will be based on the mode seleected
`rocket replay --mode [mission|simulation]`

if mission mode is selected run
`rocket replay --mode mission --mission 20250504`

> **Note**
> If simulation is getting errors about missing keys, it just means the current simulation data is no longer valid.
> Run `rm -rf backend/simulation/cache`

if simulation mode is selected run
`rocket replay --mode simulation --simulation TEST`

### List of available replays

<table>
  <thead>
    <tr>
      <th>Date</th>
      <th>Location</th>
      <th>Rocket</th>
      <th>Flight computer</th>
      <th>Start command</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>2025-05-04</td>
      <td>Serpentine, AU</td>
      <td><b style="color:#01b482">Legacy</b></td>
      <td></td>
      <td><code>rocket replay --mode mission --mission 20250504</code></td>
    </tr>
    <tr>
      <td></td>
      <td>IREC 2025</td>
      <td><b style="color:#01b482">Legacy</b></td>
      <td></td>
      <td><code>rocket replay --mode mission --mission IREC2025</code></td>
    </tr>
    <tr>
      <td rowspan=2>2026-04-28</td>
      <td rowspan=2>White Cliffs, AU</td>
      <td rowspan=2><b style="color:#f76a2a">Horizon</b></td>
      <td>AV2</td>
      <td><code>rocket replay --mode mission --mission 20260428</code></td>
    </tr>
    <tr>
      <td>Blue Raven</td>
      <td><code>rocket replay --mode mission --blue-raven 20260428</code></td>
    </tr>
    <tr>
      <td rowspan=2>2026-06-20</td>
      <td rowspan=2>IREC 2026</td>
      <td rowspan=2><b style="color:#f76a2a">Horizon</b></td>
      <td>AV2</td>
      <td><code>rocket replay --mode mission --mission IREC2026</code></td>
    </tr>
    <tr>
      <td>Blue Raven</td>
      <td><code>rocket replay --mode mission --blue-raven IREC2026</code></td>
    </tr>
  </tbody>
</table>
