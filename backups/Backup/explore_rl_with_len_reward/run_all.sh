# LSRL_EXP_NAME=hint_explore python main_rl.py
LSRL_INS_P_VER=v2 LSRL_EXP_NAME=conventional_v2 python main_rl.py


for step in 0 20 40 60 80 100 120 140 160; do
    LSRL_INS_P_VER=v2 LSRL_EXP_NAME=conventional_v2 python main_rl.py test $step
done

# LSRL_INS_P_VER=v2 LSRL_EXP_NAME=hint_explore_v2 python main_rl.py test 0

# LSRL_INS_P_VER=v2 LSRL_EXP_NAME=hint_explore_v2 python main_rl.py test 1000

# for step in 100 200 300 400 500 600 700 800 900 1000; do
#     LSRL_INS_P_VER=v2 LSRL_EXP_NAME=hint_explore_v2 python main_rl.py test $step
# done

# for step in 0 20 40 60 80 100 120 140 160 180 200; do
#     LSRL_INS_P_VER=v2 LSRL_EXP_NAME=hint_explore_v2 python main_rl.py test $step
# done

# LSRL_EXP_NAME=explore python main_rl.py
# LSRL_EXP_NAME=hint python main_rl.py
# LSRL_EXP_NAME=baseline python main_rl.py
