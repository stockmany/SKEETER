import os
import subprocess
import pandas as pd
import plotly.graph_objs as go

def calculate_harmonic_mean(alignment_length, num_matches):
    return 2 * ((alignment_length * num_matches) / (alignment_length + num_matches))

def process_paf(input_file, output_folder):
    unique_queries = {}

    with open(input_file, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            query_name = parts[0]
            alignment_length = int(parts[10])
            num_matches = int(parts[9])
            target_name_parts = parts[5].split('_')

            # Discard the first identifier and keep the rest as species name
            species_name = '_'.join(target_name_parts[1:])

            # Calculate harmonic mean
            harmonic_mean = calculate_harmonic_mean(alignment_length, num_matches)

            if query_name not in unique_queries:
                unique_queries[query_name] = {'species_name': species_name,
                                              'alignment_length': alignment_length,
                                              'num_matches': num_matches,
                                              'harmonic_mean': harmonic_mean}
            else:
                if harmonic_mean > unique_queries[query_name]['harmonic_mean']:
                    unique_queries[query_name] = {'species_name': species_name,
                                                  'alignment_length': alignment_length,
                                                  'num_matches': num_matches,
                                                  'harmonic_mean': harmonic_mean}

    # Convert dictionary to DataFrame
    df = pd.DataFrame.from_dict(unique_queries, orient='index')

    # Save DataFrame to CSV
    output_file = os.path.join(output_folder, "csv_files", os.path.splitext(os.path.basename(input_file))[0] + ".csv")
    df.to_csv(output_file)

    # Read the CSV file into a DataFrame
    df = pd.read_csv(output_file)

    # Count the number of unique species names
    unique_species = df['species_name'].nunique()

    # Print the unique species names with their occurrences
    species_counts = df['species_name'].value_counts()

    # Count the total number of lines (excluding headers)
    total_lines = len(df)

    # Filter species counts >= 20
    species_counts_filtered = species_counts[species_counts >= 20]

    # Calculate relative abundance for species names with counts >= 20
    relative_abundance = (species_counts_filtered / total_lines) * 100

    # Set species with percentages <= 1 to "other <1%"
    relative_abundance[relative_abundance <= 1] = 0
    relative_abundance['other <1%'] = relative_abundance[relative_abundance <= 1].sum()
    relative_abundance = relative_abundance[relative_abundance > 1]

    # Print the relative abundance for species names with counts >= 20
    print("Relative abundance for species names with counts >= 20:")
    print(relative_abundance)

    # Add file name, species name, and abundance percentages to a list
    file_name = os.path.splitext(os.path.basename(input_file))[0]
    abundance_data = [{'File Name': file_name, 'Species Name': species, 'Abundance Percentage': relative_abundance[species]} for species in relative_abundance.index]

    return abundance_data

def run_minimap2(input_folder, reference_file, output_folder):
    # Create output folders if they don't exist
    paf_output_folder = os.path.join(output_folder, "paf_files")
    csv_output_folder = os.path.join(output_folder, "csv_files")
    os.makedirs(paf_output_folder, exist_ok=True)
    os.makedirs(csv_output_folder, exist_ok=True)

    # List all files in the input folder
    files = os.listdir(input_folder)

    # Filter only FASTQ and FASTA files
    query_files = [f for f in files if f.endswith('.fastq') or f.endswith('.fasta')]

    # Run Minimap2 on each query file
    for query_file in query_files:
        output_paf = os.path.join(paf_output_folder, os.path.splitext(query_file)[0] + ".paf")
        with open(output_paf, 'w') as f:
            print("Minimap2 is running")
            subprocess.run(['minimap2', '-x', 'sr', reference_file, os.path.join(input_folder, query_file)], stdout=f, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    input_folder = input("Enter the path to the folder containing FASTQ and FASTA files: ")
    reference_file = input("Enter the path to the reference genome file: ")
    output_folder = "output"

    # Create output directory if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Run Minimap2 on all query files in the folder
    run_minimap2(input_folder, reference_file, output_folder)

    # Process PAF files and generate output CSV and PNG
    abundance_data_list = []
    for paf_file in os.listdir(os.path.join(output_folder, "paf_files")):
        if paf_file.endswith(".paf"):
            abundance_data_list.extend(process_paf(os.path.join(output_folder, "paf_files", paf_file), output_folder))

    # Create DataFrame from abundance data list
    abundance_df = pd.DataFrame(abundance_data_list)

    # Save DataFrame to CSV
    abundance_csv_file = os.path.join(output_folder, "abundance_data.csv")
    abundance_df.to_csv(abundance_csv_file, index=False)

    print(f"Abundance data saved to {abundance_csv_file}.")

    # Group data by species names
    grouped_data = abundance_df.groupby('Species Name')

    # Initialize lists to store traces and file names for legends
    traces = []
    file_names = set()

    # Create traces for each species name group
    for species_name, group in grouped_data:
        # Sort the group by file name for consistent colors in legends
        sorted_group = group.sort_values(by='File Name')
        
        # Append file names for legends
        file_names.update(sorted_group['File Name'])
        
        # Create bar trace for each species
        trace = go.Bar(
            x=sorted_group['File Name'],
            y=sorted_group['Abundance Percentage'],
            name=species_name
        )
        traces.append(trace)

    # Create layout
    layout = go.Layout(
        title="Abundance Percentage by Species Name",
        xaxis=dict(title='File Name'),
        yaxis=dict(title='Abundance Percentage'),
        barmode='group',
        legend=dict(title='Species Names')
    )

    # Create figure
    fig = go.Figure(data=traces, layout=layout)

    # Save plot as HTML file
    plot_file = os.path.join(output_folder, "abundance_plot.html")
    fig.write_html(plot_file)

    print(f"Plot saved as {plot_file}. Open the file in a web browser to view the plot.")
