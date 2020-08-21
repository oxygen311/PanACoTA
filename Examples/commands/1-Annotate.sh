# With prokka
PanACoTA annotate -d Examples/genomes_init -r Examples/1-res-prokka -l Examples/input_files/list_genomes.lst -n EXAM --l90 3 --nbcont 10


# With prodigal
PanACoTA annotate -d Examples/genomes_init -r Examples/1-res-prodigal -l Examples/input_files/list_genomes.lst -n EXAM  --l90 3 --prodigal --small 
