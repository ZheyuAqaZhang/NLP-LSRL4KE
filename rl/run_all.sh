# E2GRPO
LSRL_INS_P_VER=v3 LSRL_EXP_NAME=hint_v3 python main_rl.py

for step in 0 20 40 60 80 100 120 140 160 180 200; do
    LSRL_INS_P_VER=v3 LSRL_EXP_NAME=hint_v3 python main_rl.py test $step
done

# Conventional GRPO
LSRL_INS_P_VER=v3 LSRL_EXP_NAME=conventional_v3 python main_rl.py

for step in 0 20 40 60 80 100 120 140 160 180 200; do
    LSRL_INS_P_VER=v3 LSRL_EXP_NAME=conventional_v3 python main_rl.py test $step
done
