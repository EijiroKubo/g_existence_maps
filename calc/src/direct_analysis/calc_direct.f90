Module variables 
    implicit none 
    integer::i_mesh , j_mesh 
    integer,allocatable,dimension(:,:)::dir_dat
    real(8),allocatable,dimension(:,:)::exist_dat

END Module variables

!推定生息分布より、どの地点で発生している可能性があるかを推定するためのプログラム
!to compile: ifort -shared -fPIC calc_direct.f90 -o calc_direct.so 
Module CalcDir
    use variables 
    implicit none 
    
contains

    !メッシュサイズを設定
    subroutine set_mesh_size( i_mesh_num , j_mesh_num ) bind(C)
        use variables
        implicit none 
        integer,intent(in)::i_mesh_num , j_mesh_num 

            i_mesh = i_mesh_num 
            j_mesh = j_mesh_num 

            allocate( dir_dat( i_mesh , j_mesh ) , exist_dat( i_mesh , j_mesh )  )
    End subroutine set_mesh_size


    !生息分布データを受け取る
    subroutine set_existmat( exist_mat_in ) bind(C)
        use variables 
        implicit none
        real(8),dimension(i_mesh , j_mesh ),intent(in)::exist_mat_in 
        integer::i,j,k 

        exist_dat(:,:) = exist_mat_in(:,:)

    end subroutine set_existmat

    !calc_dir_mat -> out_dir_mat を実行する========================================
    subroutine get_dirmat( dir_mat_out , i_mesh_num , j_mesh_num ) bind(C)
        use variables 
        implicit none 
        integer,intent( in ) :: i_mesh_num , j_mesh_num 
        integer,dimension( i_mesh_num , j_mesh_num ),intent(inout)::dir_mat_out

        call calc_dir_dat
        call out_dir_mat( dir_mat_out , i_mesh_num , j_mesh_num )
        !call output_to_check( dir_dat )
        !call output_to_check_r( exist_dat )

    end subroutine get_dirmat


    !生息分布データに基づき、方向を算出
    subroutine calc_dir_dat() bind(C)
        use variables 
        implicit none 
        integer:: i , j , k
        integer:: ii , jj 
        integer:: ii_max , jj_max 
        real(8),parameter:: err = 0.0001
        real(8)::v_max  

        integer,dimension(3,3)::dir_tmp

        ! dir_datの元データ:dirは以下のイメージで作成する。
        ! 315 360  45 !
        ! 270   0  90 !
        ! 225 180 135 !        
        dir_tmp( 1, 1 ) = 315 ; dir_tmp( 1, 2 ) = 360 ; dir_tmp( 1, 3 ) = 45 
        dir_tmp( 2, 1 ) = 270 ; dir_tmp( 2, 2 ) =   0 ; dir_tmp( 2, 3 ) = 90
        dir_tmp( 3, 1 ) = 225 ; dir_tmp( 3, 2 ) = 180 ; dir_tmp( 3, 3 ) = 135

        dir_dat(:,:) = 0 


        !一番角を除き、すべてのメッシュを対象に計算
        do i = 2 , i_mesh - 1 
        do j = 2 , j_mesh - 1 

            v_max = 0.0 ; ii_max = 2 ; jj_max = 2
            do ii = -1 , 1 
            do jj = -1 , 1 
                !周辺メッシュで最も大きいメッシュを記録
                if( exist_dat( i + ii , j + jj ) >= v_max + err ) then 
                    v_max = exist_dat( i + ii , j + jj ) 
                    ii_max = ii + 2 !ii は -1から始まっている
                    jj_max = jj + 2 !jj は -1から始まっている
                end if 

            end do 
            end do 

            !dirの設定
            dir_dat( i, j ) = dir_tmp( ii_max , jj_max )
        
        end do 
        end do 
    end subroutine calc_dir_dat

    !計算結果(dir)を送る
    subroutine out_dir_mat( dir_mat_out , i_mesh_num , j_mesh_num ) bind(C)
        use variables
        implicit none
        integer,intent( in ) :: i_mesh_num , j_mesh_num 
        integer,dimension( i_mesh_num , j_mesh_num ),intent(inout)::dir_mat_out

        !メッシュサイズのチェック
        if( i_mesh_num /= i_mesh .or. j_mesh_num /= j_mesh ) then 
            write(*,*) "wrong mesh size"            
        else 
            dir_mat_out( :, : ) = dir_dat( :, : )
            !dir_mat_out( :, : ) = int( exist_dat( : , : ) ) !check用
        end if 

    end subroutine out_dir_mat
    !=============================================================================

    subroutine output_to_check( data )
        use variables
        implicit none 
        integer,dimension( i_mesh , j_mesh ),intent(in)::data 
        integer::i,j 

        open(99 , FILE='to_check.csv' , status='unknown')
        Do i = 1, i_mesh 
            write( 99 , '( 9999(i5 , "," ) ) ' ) ( data(i, j) , j = 1,  j_mesh ) 
        end do 
        close( 99 )

    end subroutine output_to_check

    subroutine output_to_check_r( data )
        use variables
        implicit none 
        real(8),dimension( i_mesh , j_mesh ),intent(in)::data 
        integer::i,j 

        open(99 , FILE='to_check_r.csv' , status='unknown')
        Do i = 1, i_mesh 
            write( 99 , '( 9999(f5.1 , "," ) ) ' ) ( data(i, j) , j = 1,  j_mesh ) 
        end do 
        close( 99 )

    end subroutine output_to_check_r


End Module CalcDir