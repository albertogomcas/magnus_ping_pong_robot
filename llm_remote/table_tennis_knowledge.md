# Table Tennis Knowledge for Magnus Robot

## Physical Setup

- The robot is **centered on the table**. `pan=0` sends the ball to the **middle** of the table.
- **Pan right → forehand** side of the opponent.
- **Pan left → backhand** side of the opponent.
- Tilt positive = launcher points up. Tilt negative = launcher points down.

---

## Spin Physics

### Topspin
- The ball dips faster than a flat shot — it drops toward the table sooner.
- To compensate and clear the net, either:
  - **Increase tilt** (aim slightly higher), or
  - **Increase speed** (more forward momentum to carry it over).
- Prefer increasing tilt for small adjustments. Prefer increasing speed when the ball is already landing close to the net end of the table.

### Backspin
- The ball floats and descends slower than a flat shot — it carries further.
- To compensate and keep the ball on the table, either:
  - **Decrease speed** (less forward momentum), or
  - **Decrease tilt** (aim slightly lower).
- Caution: decreasing tilt too much will shoot the ball straight into the net. Prefer decreasing speed first.

### Sidespin (left / right)
- The ball curves horizontally in the direction of the spin.
- Combine with pan adjustments to keep the landing point on target.

### No spin (flat)
- Baseline reference. Ball follows a predictable arc.
- Use as starting point when calibrating aim.

---

## Practical Guidelines

| Goal | What to adjust |
|---|---|
| Ball hits the net (too low) | Increase tilt, or increase speed |
| Ball overshoots the table (too far) | Decrease tilt, or decrease speed |
| Adding topspin | Slightly increase tilt or speed to compensate |
| Adding backspin | Slightly decrease speed first; decrease tilt only if needed |
| Targeting forehand | Increase pan (positive = right) |
| Targeting backhand | Decrease pan (negative = left) |
| Targeting center | Set pan to 0 |

---

## Suggested Starting Parameters

| Shot type | Speed | Tilt offset | Notes |
|---|---|---|---|
| Flat / no spin | 50 | 0 | Baseline |
| Topspin | 55 | +2° | Compensate for ball dip |
| Backspin | 42 | 0 | Reduce speed first |
| Left sidespin | 50 | 0 | Adjust pan slightly right to compensate curve |
| Right sidespin | 50 | 0 | Adjust pan slightly left to compensate curve |

These are starting points — fine-tune with `aim_up` / `aim_down` and `speed_up` / `speed_down` after observing the ball trajectory.

