import shutil
from argparse import ArgumentParser
from pathlib import Path

parser = ArgumentParser(
    description="Generate a synthetic dbt project."
)

parser.add_argument(
    "--layers",
    type=int,
    default=5,
    help="Number of dependency layers.",
)

parser.add_argument(
    "--width",
    type=int,
    default=4,
    help="Number of models in each layer.",
)

parser.add_argument(
    "--expressions",
    type=int,
    default=10,
    help="Calculated Jinja/SQL columns per model.",
)

parser.add_argument(
    "--test-every",
    type=int,
    default=5,
    help="Add tests to every Nth generated model. Use 0 for no tests.",
)

args = parser.parse_args()

if args.layers < 1:
    raise ValueError("--layers must be at least 1")

if args.width < 1:
    raise ValueError("--width must be at least 1")

if args.expressions < 1:
    raise ValueError("--expressions must be at least 1")

generated_directory = Path("models/generated")

if generated_directory.exists():
    shutil.rmtree(generated_directory)

generated_directory.mkdir(parents=True)

schema_entries = []
model_index = 0

for layer in range(1, args.layers + 1):
    for branch in range(1, args.width + 1):
        model_index += 1

        model_name = f"model_l{layer:03d}_b{branch:03d}"

        if layer == 1:
            primary_model = "base_events"
            secondary_model = "base_events"
        else:
            primary_model = (
                f"model_l{layer - 1:03d}_b{branch:03d}"
            )

            secondary_branch = (
                branch - 1 if branch > 1 else args.width
            )

            secondary_model = (
                f"model_l{layer - 1:03d}_b{secondary_branch:03d}"
            )

        sql = f"""{{{{ config(materialized='table') }}}}

with primary_data as (

    select
        id,
        customer_id,
        product_id,
        customer_group,
        country,
        amount,
        event_timestamp
    from {{{{ ref('{primary_model}') }}}}

),

secondary_statistics as (

    select
        customer_group,
        count(*) as group_event_count,
        avg(amount) as group_average_amount
    from {{{{ ref('{secondary_model}') }}}}
    group by customer_group

),

enriched as (

    select
        p.id,
        p.customer_id,
        p.product_id,
        p.customer_group,
        p.country,
        p.amount,
        p.event_timestamp,

        s.group_event_count,
        s.group_average_amount,

        row_number() over (
            partition by p.customer_group
            order by p.event_timestamp, p.id
        ) as group_row_number,

        lag(p.amount) over (
            partition by p.customer_id
            order by p.event_timestamp, p.id
        ) as previous_amount,

        avg(p.amount) over (
            partition by p.customer_group
            order by p.event_timestamp, p.id
            rows between 10 preceding and current row
        ) as rolling_average_amount,

        md5(
            cast(p.id as varchar)
            || '-{layer}-{branch}'
        ) as record_hash

        {{{{ synthetic_columns(
            'p',
            {layer},
            {args.expressions}
        ) }}}}

    from primary_data as p

    left join secondary_statistics as s
        on p.customer_group = s.customer_group

)

select *
from enriched
"""

        output_path = generated_directory / f"{model_name}.sql"
        output_path.write_text(sql, encoding="utf-8")

        schema_entry = [
            f"  - name: {model_name}",
            f"    description: Synthetic model in layer {layer}, branch {branch}.",
        ]

        if args.test_every > 0 and model_index % args.test_every == 0:
            schema_entry.extend(
                [
                    "    columns:",
                    "      - name: id",
                    "        data_tests:",
                    "          - not_null",
                    "      - name: customer_group",
                    "        data_tests:",
                    "          - not_null",
                ]
            )

        schema_entries.append("\n".join(schema_entry))

schema_content = (
    "version: 2\n"
    "models:\n"
    + "\n".join(schema_entries)
    + "\n"
)

schema_path = generated_directory / "schema_generated.yml"
schema_path.write_text(schema_content, encoding="utf-8")

total_models = args.layers * args.width

print()
print("Synthetic dbt project generated")
print(f"Layers:                 {args.layers}")
print(f"Models per layer:       {args.width}")
print(f"Generated models:       {total_models}")
print(f"Models including base:  {total_models + 1}")
print(f"Expressions per model:  {args.expressions}")
print(f"Test every Nth model:   {args.test_every}")
print(f"Output directory:       {generated_directory}")