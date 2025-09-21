# Quick Script to Show Perfect Format Example
import pandas as pd

# Create the exact example format you provided
example_data = {
    'Company Name': [
        'Forest Stewardship Council',
        'Polestar'
    ],
    'Company Description': [
        'Promoting sustainable forestry to combat climate and biodiversity crises globally.',
        'Driving society forward with uncompromised electric performance and progressive innovation.'
    ],
    'Website URL': [
        'https://fsc.org/en',
        'https://www.polestar.com/'
    ],
    'Linkedin URL': [
        'https://www.linkedin.com/company/fsc-international-bonn/',
        'https://www.linkedin.com/company/polestarcars/posts/'
    ],
    'Careers Page URL': [
        'https://fsc.org/en/careers-at-fsc',
        'https://www.polestar.com/global/about/careers/'
    ],
    'Job listings page URL': [
        'https://fsc.org/en/careers-at-fsc',
        'https://polestar.teamtailor.com/jobs'
    ],
    'job post1 URL': [
        'https://fsc.jobs.personio.com/job/2005656?language=en%3Flanguage%3D&display=en',
        'https://polestar.teamtailor.com/jobs/5648292-controller-brand-marketing-pr-events'
    ],
    'job post1 title': [
        'Media Relations Manager (m-f-d)',
        'Controller | Brand & Marketing, PR & Events'
    ],
    'job post2 URL': [
        'https://fsc.jobs.personio.com/job/1962742?language=en%3Flanguage%3D&display=en',
        'https://polestar.teamtailor.com/jobs/5642478-financial-controller-manufacturing'
    ],
    'job post2 title': [
        'Market Development Officer (m-f-d) - Southern Africa',
        'Financial Controller Manufacturing'
    ],
    'job post3 URL': [
        'https://fsc.jobs.personio.com/job/1996890?language=en%3Flanguage%3D&display=en',
        'https://polestar.teamtailor.com/jobs/5587912-senior-business-controller-polestar-sweden'
    ],
    'job post3 title': [
        'EUDR Policy & Chain-of-Custody Manager, FSC Asia-Pacific (m-f-d)',
        'Senior Business Controller | Polestar Sweden'
    ]
}

# Create DataFrame
df_example = pd.DataFrame(example_data)

# Save to Excel
df_example.to_excel('Perfect_Format_Example.xlsx', index=False)

# Print in the exact format requested
print("PERFECT FORMAT EXAMPLE:")
print("=" * 100)

# Header
headers = list(df_example.columns)
print('\t'.join(headers))

# Data rows  
for idx in range(len(df_example)):
    row_values = []
    for col in headers:
        row_values.append(str(df_example.iloc[idx][col]))
    print('\t'.join(row_values))

print("\n" + "=" * 100)
print("This is the EXACT format you requested!")
print("File saved as: Perfect_Format_Example.xlsx")
print("=" * 100)