Module variables 
    implicit none 
    integer::i_mesh , j_mesh , timesteps , obs_num , parallel_threads

    real(8),allocatable,dimension(:,:)::grid_x , grid_y
    real(8),allocatable,dimension(:,:)::obs
    real(8):: sigma, C_coff , D_coff


END Module variables

Module CalcExist
    use variables 
    !$ use omp_lib    
    implicit none 
   
contains

    !メッシュサイズを設定
    subroutine set_mesh_data( j_mesh_num , i_mesh_num  , timesteps_in , grid_x_in , grid_y_in ) bind(C)
        use variables
        implicit none 
        integer,intent(in)::i_mesh_num , j_mesh_num , timesteps_in
        real(8),dimension( j_mesh_num , i_mesh_num ),intent(in)::grid_x_in , grid_y_in 

            i_mesh = i_mesh_num 
            j_mesh = j_mesh_num 
            timesteps = timesteps_in

            allocate( grid_x( j_mesh , i_mesh ) , grid_y( j_mesh , i_mesh ) )

            grid_x(:,:) = grid_x_in(:,:)
            grid_y(:,:) = grid_y_in(:,:)

    End subroutine set_mesh_data

    !観測データを記録:obs_num -> データ数 , obs_in( 1 = x / 2 = y / 3 = day , length ) , x / y in meter 
    subroutine set_observation( obs_num_in , obs_in ) bind(C)
        use variables
        implicit none 
        integer,intent(in)::obs_num_in
        real(8),dimension( obs_num_in , 3 ),intent(in)::obs_in
        integer::i,j

        allocate( obs( obs_num_in  , 3 ) )
        obs( :, : )  = obs_in
        obs_num = obs_num_in 

    end subroutine set_observation

    !計算に必要なパラメータをセットする
    subroutine set_parameters( sigma_in , C_coff_in , D_coff_in , parallel_threads_in ) bind(C)
        use variables
        implicit none 
        real(8),intent(in):: sigma_in, C_coff_in , D_coff_in
        integer,intent(in):: parallel_threads_in 
        

        ! sigma  :初期生息分布を構成するために使用するガウス関数のパラメータ：スカラー値としている
        ! C_coff :移流係数
        ! D_coff :拡散係数
        ! 並列計算スレッド数
     
        sigma = sigma_in    
        C_coff = C_coff_in
        D_coff = D_coff_in
        parallel_threads = parallel_threads_in 
    
    end subroutine set_parameters

    !生息分布を計算
    subroutine calc_existence_fokkerplanck( max_passed_days , days_to_lookback  , days_to_predict , result ) bind(C)
        use variables
        implicit none 
        real(8),intent(in):: max_passed_days , days_to_lookback , days_to_predict 
        real(8),dimension( j_mesh , i_mesh , timesteps )::result

        integer:: loops 
        real(8):: days_to_calc , time , days_to_outcalc , days_of_startoutput , time_tmp_out , dt_to_output , dt_calc
        real(8),parameter:: dt_calc_default = 0.1 
        real(8),dimension( obs_num )::obs_date_tmp
        real(8),dimension( j_mesh , i_mesh ):: exist , exist_tmp

        integer::i , j , k , l , ts_out_count
        real(8):: adv_j , adv_i ,adv_j_up , adv_j_dw , adv_i_r , adv_i_l , diff_j , diff_i , dpxdt , dpydt
        real(8)::test_tp

        ! max_passed_days :計算対象のうち、最も古いデータに対する経過日数
        ! days_to_lookbask:現時刻以前の計算日数
        ! days_to_predict :現時刻以降の計算日数
        
        !メモ：計算結果は最も古いデータから追っていく必要があるが、
        !興味のある計算結果は、days_to_lookback(過去OO日) ~ days_to_pridict(未来OO日)、のように設定した範囲とする。
        
        days_to_calc = max_passed_days + days_to_predict          !全計算日数
        days_to_outcalc = days_to_lookback + days_to_predict      !全計算出力日数
        dt_to_output = days_to_outcalc / dble( timesteps )        !出力のステップ間隔

        if( dt_to_output < dt_calc_default ) then
            dt_calc = dt_to_output 
        else 
            dt_calc = dt_calc_default 
        end if 

        loops = int(  days_to_calc / dt_calc )                    !ループ数を計算
        

        !観測データについて：最も古い観測日からの経過日数を計算
        Do k = 1 , obs_num
            obs_date_tmp( k ) = ( obs( k , 3 ) - max_passed_days ) * ( -1.0 )
        End Do 

        !最も古い観測日からの計算開始時点を計算
        days_of_startoutput = ( days_to_lookback - max_passed_days ) * ( -1.0 )

        !parallel computing
        !$ call omp_set_num_threads(parallel_threads)
        !$ write(*,*) "threads;" , parallel_threads


        !Fokker-Planck Equation
        time = 0 ;  exist_tmp(:,:) = 0.0 ; exist_tmp(:,:) = 0.0 ; time_tmp_out= 0.0 ; ts_out_count = 0 
        Do k = 1 , loops 
            time = time + dt_calc

            !FP方程式
            !$omp parallel do private(i,adv_j,adv_j_up,adv_j_dw,adv_i,adv_i_r,adv_i_l,diff_i,diff_j,dpxdt,dpydt) 
            Do j = 2 , j_mesh - 1 
            Do i = 2 , i_mesh - 1 
                adv_j     = ( exist_tmp(j+1,i  )-exist_tmp(j  ,i  ))/ abs( grid_x(j+1,i  )-grid_x(j  ,i  ) )
                adv_j_up  = ( exist_tmp(j+1,i-1)-exist_tmp(j  ,i-1))/ abs( grid_x(j+1,i-1)-grid_x(j  ,i-1) )
                adv_j_dw  = ( exist_tmp(j+1,i+1)-exist_tmp(j  ,i+1))/ abs( grid_x(j+1,i+1)-grid_x(j  ,i+1) )
                adv_i     = ( exist_tmp(j  ,i+1)-exist_tmp(j  ,i  ))/ abs( grid_y(j  ,i+1)-grid_y(j  ,i  ) ) 
                adv_i_r   = ( exist_tmp(j+1,i+1)-exist_tmp(j+1,i  ))/ abs( grid_y(j+1,i+1)-grid_y(j+1,i  ) )
                adv_i_l   = ( exist_tmp(j-1,i+1)-exist_tmp(j-1,i  ))/ abs( grid_y(j-1,i+1)-grid_y(j-1,i  ) )                

                diff_i    = ( adv_j_up - adv_j_dw ) / abs( grid_y( j , i + 1 ) - grid_y( j , i - 1 ) )
                diff_j    = ( adv_i_r - adv_i_l )   / abs( grid_x( j + 1 , i ) - grid_x( j - 1 , i ) )

                dpxdt     = ( C_coff * adv_j + D_coff * diff_j ) 
                dpydt     = ( C_coff * adv_i + D_coff * diff_i ) 

                exist( j , i ) = exist_tmp( j , i )  & 
                            &  - (  ( C_coff * adv_j ) + ( C_coff + adv_i ) ) * dt_calc 
                            !&  + (  D_coff * diff_j + D_coff * diff_i ) / 2.0 ) * dt_calc 

            End Do 
            End Do 
            !$omp end parallel do
            

            !初期発覚時の生息分布を計算
            !$omp parallel do private( l , i , j )
            Do l = 1 , obs_num
                IF( obs_date_tmp(l) >= time - dt_calc .and. obs_date_tmp(l) < time ) then             

                    Do j = 1 , j_mesh 
                    Do i = 1 , i_mesh
                        exist( j , i ) = exist( j , i ) & 
                        & + exp( -1.0 * ( ( grid_x(j,i) - obs(l,1) ) ** 2.0 + ( ( grid_y(j,i) - obs(l,2) ) ** 2.0 ) ) / ( sigma ) )                         
                        
                    End DO
                    End DO 

                End If 
            End do 
            !$omp end parallel do         

            !boundary 
            exist( 1 , : ) = 0.0 
            exist( j_mesh , : ) = 0.0 
            exist( : , 1 ) = 0.0 
            exist( : , i_mesh ) = 0.0 

            !次ステップ用tmpデータ
            exist_tmp(:,:) = exist(:,:) 

            !計算結果記録
            if( time > days_of_startoutput ) then 
                time_tmp_out = time_tmp_out + dt_calc  
                
                if(     dble( ts_out_count ) * dt_to_output >= time_tmp_out - dt_calc .and. & 
                    &   dble( ts_out_count ) * dt_to_output < time_tmp_out ) then 
                        ts_out_count = ts_out_count + 1 
                        result( : , : , ts_out_count ) = exist( : , : )
                        write(*,*) ts_out_count, time 
                end if 
                
            end if 
        END DO 

    end subroutine calc_existence_fokkerplanck


End Module CalcExist
