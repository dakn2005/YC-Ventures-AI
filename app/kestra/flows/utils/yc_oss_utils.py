def build_title(row: dict) -> str:
  name = row.get("name") or ""

  if row.get("one_liner"):
    return f"{name} — {row['one_liner']}"

  return name


def build_content(row: dict) -> str:
  lines = []

  # if row.get("former_names"):
  #   lines.append("Formerly known as: " + ", ".join(row["former_names"]))

  if row.get("long_description"):
    lines.append(row["long_description"])

  tags_line = []
  if row.get("industries"):
    tags_line.append("Industries: " + ", ".join(row["industries"]))
  if row.get("subindustry"):
    tags_line.append(f"Subindustry: {row['subindustry']}")
  if row.get("tags"):
    tags_line.append("Tags: " + ", ".join(row["tags"]))
  if tags_line:
    lines.append(" | ".join(tags_line))

  where = []
  if row.get("locations"):
    where.append(f"Location: {row['locations']}")
  if row.get("regions"):
    where.append("Regions: " + ", ".join(row["regions"]))
  if where:
    lines.append(" | ".join(where))

  status_bits = []
  if row.get("stage"):
    status_bits.append(f"Stage: {row['stage']}")
  if row.get("batch"):
    status_bits.append(f"YC batch: {row['batch']}")
  if row.get("status"):
    status_bits.append(f"Status: {row['status']}")
  if row.get("launched_at"):
    status_bits.append(f"Launched: {row['launched_at']:%Y-%m-%d}")
  if row.get("team_size"):
    status_bits.append(f"Team size: {row['team_size']}")
  if status_bits:
    lines.append(" | ".join(status_bits))

  flags = []
  if row.get("is_hiring"):
    flags.append("actively hiring")
  if row.get("top_company"):
    flags.append("marked a top company")
  if row.get("non_profit"):
    flags.append("a non-profit")
  if flags:
    lines.append("This company is " + ", ".join(flags) + ".")

  return "\n".join(lines)
