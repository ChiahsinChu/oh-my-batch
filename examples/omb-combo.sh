#! /bin/bash
# prepare fake data files
mkdir -p tmp/
touch tmp/1.data tmp/2.data tmp/3.data

# prepare a lammps input file template
cat > tmp/in.lmp.tmp <<EOF
read_data data.lmp
velocity all create @TEMP @RANDOM
run 1000
EOF

# prepare a run script template
cat > tmp/run.sh.tmp <<EOF
cat in.lmp  # simulate running lammps
EOF

# generate input files
omb combo \
    add_files DATA_FILE tmp/*.data - \
    add_var TEMP 300 400 500 - \
    add_randint RANDOM -n 3 -a 1 -b 1000 - \
    set_broadcast RANDOM - \
    make_files tmp/tasks/{i}-T-{TEMP}/in.lmp --template tmp/in.lmp.tmp - \
    make_files tmp/tasks/{i}-T-{TEMP}/run.sh --template tmp/run.sh.tmp --mode 755 - \
    run_cmd "cp {DATA_FILE} tmp/tasks/{i}-T-{TEMP}/data.lmp" - \
    done
